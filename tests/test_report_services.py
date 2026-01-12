"""Tests for the report service layer.

Comprehensive tests covering weekly status data, monthly statistics,
and CSV export functionality.
"""
import csv
import io
import pytest
from datetime import date, datetime, timedelta, timezone

from app import db
from app.models import Project, ProjectStatus
from app.services import create_project
from app.services.report_service import (
    get_weekly_status_data,
    get_monthly_stats,
    export_projects_csv,
    get_available_weekly_fields,
    DEFAULT_WEEKLY_FIELDS,
)


class TestGetWeeklyStatusData:
    """Tests for get_weekly_status_data function."""

    def test_returns_only_active_projects(self, app):
        """Should exclude completed projects from weekly status."""
        with app.app_context():
            # Create an active project
            create_project({
                'project_name': 'Active Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 2, 1),
                'status': ProjectStatus.IN_PROGRESS,
            })

            # Create a completed project
            create_project({
                'project_name': 'Completed Project',
                'department': 'Finance',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.COMPLETED,
            })

            result = get_weekly_status_data()

            assert len(result) == 1
            assert result[0]['project_name'] == 'Active Project'

    def test_excludes_deleted_projects(self, app):
        """Should exclude soft-deleted projects from weekly status."""
        with app.app_context():
            # Create a project
            project = create_project({
                'project_name': 'To Be Deleted',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            # Soft delete it
            project.deleted_at = datetime.now(timezone.utc)
            db.session.commit()

            result = get_weekly_status_data()
            assert len(result) == 0

    def test_returns_only_requested_fields(self, app):
        """Should include only the fields specified in the request."""
        with app.app_context():
            create_project({
                'project_name': 'Test Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 2, 1),
            })

            result = get_weekly_status_data(fields=['project_name', 'department'])

            assert len(result) == 1
            assert set(result[0].keys()) == {'project_name', 'department'}
            assert result[0]['project_name'] == 'Test Project'
            assert result[0]['department'] == 'Public Works'

    def test_field_rename_delivery_deadline_to_anticipated_completion(self, app):
        """Should rename delivery_deadline to anticipated_completion in output."""
        with app.app_context():
            create_project({
                'project_name': 'Test Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 2, 15),
            })

            result = get_weekly_status_data(fields=['project_name', 'anticipated_completion'])

            assert len(result) == 1
            assert 'anticipated_completion' in result[0]
            assert 'delivery_deadline' not in result[0]
            assert result[0]['anticipated_completion'] == '2026-02-15'

    def test_default_fields_when_none_specified(self, app):
        """Should use default fields when none are specified."""
        with app.app_context():
            create_project({
                'project_name': 'Test Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 2, 1),
            })

            result = get_weekly_status_data()

            assert len(result) == 1
            # Check that default fields are present
            for field in DEFAULT_WEEKLY_FIELDS:
                assert field in result[0]

    def test_empty_result_when_no_active_projects(self, app):
        """Should return empty list when no active projects exist."""
        with app.app_context():
            # Create only completed projects
            create_project({
                'project_name': 'Completed',
                'department': 'Finance',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.COMPLETED,
            })

            result = get_weekly_status_data()
            assert result == []

    def test_sorted_by_delivery_deadline(self, app):
        """Should return projects sorted by delivery deadline ascending."""
        with app.app_context():
            # Create projects in non-sorted order
            create_project({
                'project_name': 'Later',
                'department': 'Finance',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 3, 1),
            })
            create_project({
                'project_name': 'Earlier',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 2, 1),
            })

            result = get_weekly_status_data(fields=['project_name', 'anticipated_completion'])

            assert len(result) == 2
            assert result[0]['project_name'] == 'Earlier'
            assert result[1]['project_name'] == 'Later'

    def test_null_deadlines_sorted_last(self, app):
        """Projects with null delivery_deadline should be sorted last."""
        with app.app_context():
            create_project({
                'project_name': 'No Deadline',
                'department': 'Finance',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': None,
            })
            create_project({
                'project_name': 'Has Deadline',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'delivery_deadline': date(2026, 2, 1),
            })

            result = get_weekly_status_data(fields=['project_name', 'anticipated_completion'])

            assert len(result) == 2
            assert result[0]['project_name'] == 'Has Deadline'
            assert result[1]['project_name'] == 'No Deadline'


class TestGetMonthlyStats:
    """Tests for get_monthly_stats function."""

    def test_projects_opened_count(self, app):
        """Should count projects created in the specified month."""
        with app.app_context():
            # Create project in January 2026
            project = create_project({
                'project_name': 'January Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            # Manually set created_at to ensure it's in January
            project.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
            db.session.commit()

            stats = get_monthly_stats(2026, 1)

            assert stats['projects_opened'] == 1
            assert stats['year'] == 2026
            assert stats['month'] == 1

    def test_projects_completed_count(self, app):
        """Should count projects completed in the specified month."""
        with app.app_context():
            # Create and complete a project
            project = create_project({
                'project_name': 'Completed in January',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.COMPLETED,
            })
            project.updated_at = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
            db.session.commit()

            stats = get_monthly_stats(2026, 1)

            assert stats['projects_completed'] == 1

    def test_by_department_breakdown(self, app):
        """Should provide correct breakdown by department."""
        with app.app_context():
            # Create projects in different departments
            for dept in ['Public Works', 'Public Works', 'Finance']:
                project = create_project({
                    'project_name': f'{dept} Project',
                    'department': dept,
                    'date_to_client': date(2026, 1, 1),
                    'date_assigned_to_us': date(2026, 1, 5),
                    'assigned_attorney': 'John Smith',
                    'qcp_attorney': 'Jane Doe',
                })
                project.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
                db.session.commit()

            stats = get_monthly_stats(2026, 1)

            assert stats['by_department']['Public Works'] == 2
            assert stats['by_department']['Finance'] == 1

    def test_by_attorney_breakdown(self, app):
        """Should provide correct breakdown by assigned attorney."""
        with app.app_context():
            # Create projects with different attorneys
            project1 = create_project({
                'project_name': 'Project 1',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            project1.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

            project2 = create_project({
                'project_name': 'Project 2',
                'department': 'Finance',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'Alice Johnson',
                'qcp_attorney': 'Jane Doe',
            })
            project2.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
            db.session.commit()

            stats = get_monthly_stats(2026, 1)

            assert stats['by_attorney']['John Smith'] == 1
            assert stats['by_attorney']['Alice Johnson'] == 1

    def test_avg_days_to_completion(self, app):
        """Should calculate average days to completion correctly."""
        with app.app_context():
            # Create a completed project
            project = create_project({
                'project_name': 'Completed Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 10),  # Assigned Jan 10
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.COMPLETED,
            })
            # Completed Jan 20 = 10 days later
            project.updated_at = datetime(2026, 1, 20, 10, 0, 0, tzinfo=timezone.utc)
            db.session.commit()

            stats = get_monthly_stats(2026, 1)

            assert stats['avg_days_to_completion'] == 10.0

    def test_handles_month_with_no_projects(self, app):
        """Should return zeros when no projects in month."""
        with app.app_context():
            stats = get_monthly_stats(2026, 6)

            assert stats['projects_opened'] == 0
            assert stats['projects_completed'] == 0
            assert stats['by_department'] == {}
            assert stats['by_attorney'] == {}
            assert stats['avg_days_to_completion'] is None

    def test_cross_month_boundaries(self, app):
        """Project created in Dec but completed in Jan should appear in Jan completed."""
        with app.app_context():
            project = create_project({
                'project_name': 'Cross Month Project',
                'department': 'Public Works',
                'date_to_client': date(2025, 12, 1),
                'date_assigned_to_us': date(2025, 12, 15),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'status': ProjectStatus.COMPLETED,
            })
            # Created in December
            project.created_at = datetime(2025, 12, 15, 10, 0, 0, tzinfo=timezone.utc)
            # Completed in January
            project.updated_at = datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
            db.session.commit()

            dec_stats = get_monthly_stats(2025, 12)
            jan_stats = get_monthly_stats(2026, 1)

            # Project was opened in December
            assert dec_stats['projects_opened'] == 1
            assert dec_stats['projects_completed'] == 0

            # Project was completed in January
            assert jan_stats['projects_opened'] == 0
            assert jan_stats['projects_completed'] == 1

    def test_invalid_month_raises_error(self, app):
        """Should raise ValueError for invalid month."""
        with app.app_context():
            with pytest.raises(ValueError) as excinfo:
                get_monthly_stats(2026, 13)
            assert 'Invalid month' in str(excinfo.value)

    def test_invalid_year_raises_error(self, app):
        """Should raise ValueError for invalid year."""
        with app.app_context():
            with pytest.raises(ValueError) as excinfo:
                get_monthly_stats(1800, 1)
            assert 'Invalid year' in str(excinfo.value)

    def test_excludes_deleted_projects(self, app):
        """Should not count soft-deleted projects in stats."""
        with app.app_context():
            project = create_project({
                'project_name': 'Deleted Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            project.created_at = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
            project.deleted_at = datetime.now(timezone.utc)
            db.session.commit()

            stats = get_monthly_stats(2026, 1)

            assert stats['projects_opened'] == 0


class TestExportProjectsCsv:
    """Tests for export_projects_csv function."""

    def test_returns_valid_csv_string(self, app):
        """Should return a valid CSV-formatted string."""
        with app.app_context():
            create_project({
                'project_name': 'Test Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            csv_output = export_projects_csv()

            # Should be parseable as CSV
            reader = csv.reader(io.StringIO(csv_output))
            rows = list(reader)
            assert len(rows) >= 2  # Header + at least 1 data row

    def test_includes_all_expected_columns(self, app):
        """Should include all expected column headers."""
        with app.app_context():
            create_project({
                'project_name': 'Test Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            csv_output = export_projects_csv()

            reader = csv.reader(io.StringIO(csv_output))
            headers = next(reader)

            expected_headers = [
                'ID', 'Project Name', 'Project Group', 'Department',
                'Date to Client', 'Date Assigned', 'Assigned Attorney',
                'QCP Attorney', 'Internal Deadline', 'Delivery Deadline',
                'Status', 'Notes'
            ]
            assert headers == expected_headers

    def test_notes_truncated_to_200_chars(self, app):
        """Should truncate notes longer than 200 characters."""
        with app.app_context():
            long_note = 'A' * 300
            create_project({
                'project_name': 'Test Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'notes': long_note,
            })

            csv_output = export_projects_csv()

            reader = csv.DictReader(io.StringIO(csv_output))
            row = next(reader)

            assert len(row['Notes']) == 200  # 197 + '...'
            assert row['Notes'].endswith('...')

    def test_filters_are_applied(self, app):
        """Should apply filters to the export."""
        with app.app_context():
            create_project({
                'project_name': 'Public Works Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            create_project({
                'project_name': 'Finance Project',
                'department': 'Finance',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })

            csv_output = export_projects_csv({'department': 'Finance'})

            reader = csv.DictReader(io.StringIO(csv_output))
            rows = list(reader)

            assert len(rows) == 1
            assert rows[0]['Department'] == 'Finance'

    def test_handles_empty_result_set(self, app):
        """Should return CSV with only headers when no projects match."""
        with app.app_context():
            csv_output = export_projects_csv()

            reader = csv.reader(io.StringIO(csv_output))
            rows = list(reader)

            assert len(rows) == 1  # Only header row
            assert rows[0][0] == 'ID'  # First header

    def test_csv_can_be_parsed_correctly(self, app):
        """Should produce CSV that can be fully parsed back to data."""
        with app.app_context():
            create_project({
                'project_name': 'Test Project',
                'project_group': 'Test Group',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'internal_deadline': date(2026, 1, 20),
                'delivery_deadline': date(2026, 1, 25),
                'notes': 'Test notes',
            })

            csv_output = export_projects_csv()

            reader = csv.DictReader(io.StringIO(csv_output))
            row = next(reader)

            assert row['Project Name'] == 'Test Project'
            assert row['Project Group'] == 'Test Group'
            assert row['Department'] == 'Public Works'
            assert row['Date to Client'] == '2026-01-01'
            assert row['Date Assigned'] == '2026-01-05'
            assert row['Assigned Attorney'] == 'John Smith'
            assert row['QCP Attorney'] == 'Jane Doe'
            assert row['Internal Deadline'] == '2026-01-20'
            assert row['Delivery Deadline'] == '2026-01-25'
            assert row['Status'] == 'In Progress'
            assert row['Notes'] == 'Test notes'

    def test_handles_special_characters_in_csv(self, app):
        """Should handle special characters (commas, quotes) in CSV."""
        with app.app_context():
            create_project({
                'project_name': 'Project with "quotes" and, commas',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
                'notes': 'Notes with\nnewlines',
            })

            csv_output = export_projects_csv()

            # Should be parseable despite special characters
            reader = csv.DictReader(io.StringIO(csv_output))
            row = next(reader)

            assert 'quotes' in row['Project Name']
            assert 'commas' in row['Project Name']

    def test_excludes_deleted_projects_by_default(self, app):
        """Should exclude soft-deleted projects from CSV export."""
        with app.app_context():
            project = create_project({
                'project_name': 'Deleted Project',
                'department': 'Public Works',
                'date_to_client': date(2026, 1, 1),
                'date_assigned_to_us': date(2026, 1, 5),
                'assigned_attorney': 'John Smith',
                'qcp_attorney': 'Jane Doe',
            })
            project.deleted_at = datetime.now(timezone.utc)
            db.session.commit()

            csv_output = export_projects_csv()

            reader = csv.reader(io.StringIO(csv_output))
            rows = list(reader)

            assert len(rows) == 1  # Only header, no data rows


class TestGetAvailableWeeklyFields:
    """Tests for get_available_weekly_fields function."""

    def test_returns_field_mapping(self, app):
        """Should return dictionary of internal to display names."""
        with app.app_context():
            fields = get_available_weekly_fields()

            assert isinstance(fields, dict)
            assert 'project_name' in fields
            assert fields['project_name'] == 'Project Name'
            assert 'anticipated_completion' in fields
            assert fields['anticipated_completion'] == 'Anticipated Completion'

    def test_returns_copy_not_reference(self, app):
        """Should return a copy to prevent modification of original."""
        with app.app_context():
            fields1 = get_available_weekly_fields()
            fields1['new_field'] = 'New Field'

            fields2 = get_available_weekly_fields()
            assert 'new_field' not in fields2
