/**
 * Lightweight Autocomplete Component
 * Legal Project Tracker - "Legal Precision" Theme
 *
 * Usage: Add data-autocomplete="/api/autocomplete/field_name" to input element
 * Initialize: new Autocomplete(inputElement, endpoint)
 */

class Autocomplete {
    constructor(input, endpoint) {
        this.input = input;
        this.endpoint = endpoint;
        this.dropdown = null;
        this.items = [];
        this.selectedIndex = -1;
        this.debounceTimer = null;
        this.isOpen = false;

        this.init();
    }

    init() {
        // Create dropdown element
        this.dropdown = this.createDropdown();

        // Position dropdown relative to input
        this.input.parentElement.style.position = 'relative';
        this.input.parentElement.appendChild(this.dropdown);

        // Bind events
        this.bindEvents();
    }

    createDropdown() {
        const dropdown = document.createElement('div');
        dropdown.className = 'autocomplete-dropdown';
        dropdown.style.display = 'none';
        return dropdown;
    }

    bindEvents() {
        // Input events
        this.input.addEventListener('input', (e) => this.onInput(e));
        this.input.addEventListener('focus', () => this.onFocus());
        this.input.addEventListener('blur', () => this.onBlur());
        this.input.addEventListener('keydown', (e) => this.onKeydown(e));

        // Prevent form submission on enter when dropdown is open
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && this.isOpen) {
                e.preventDefault();
            }
        });
    }

    onInput(e) {
        const value = e.target.value.trim();

        // Clear existing timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Debounce the fetch
        this.debounceTimer = setTimeout(() => {
            if (value.length >= 1) {
                this.fetchSuggestions(value);
            } else {
                this.close();
            }
        }, 150);
    }

    onFocus() {
        const value = this.input.value.trim();
        if (value.length >= 1 && this.items.length > 0) {
            this.open();
        }
    }

    onBlur() {
        // Delay close to allow click on dropdown item
        setTimeout(() => this.close(), 150);
    }

    onKeydown(e) {
        if (!this.isOpen) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectNext();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectPrev();
                break;
            case 'Enter':
                e.preventDefault();
                this.selectCurrent();
                break;
            case 'Escape':
                this.close();
                break;
        }
    }

    async fetchSuggestions(query) {
        try {
            const response = await fetch(this.endpoint);
            if (!response.ok) throw new Error('Failed to fetch suggestions');

            const data = await response.json();
            const allItems = data.data || [];

            // Filter items that match the query (case-insensitive)
            const queryLower = query.toLowerCase();
            this.items = allItems.filter(item =>
                item.toLowerCase().includes(queryLower)
            );

            this.renderDropdown();

            if (this.items.length > 0) {
                this.open();
            } else {
                this.close();
            }
        } catch (error) {
            console.error('Autocomplete fetch error:', error);
            this.close();
        }
    }

    renderDropdown() {
        this.dropdown.innerHTML = '';
        this.selectedIndex = -1;

        this.items.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'autocomplete-item';
            div.textContent = item;
            div.dataset.index = index;

            div.addEventListener('mousedown', (e) => {
                e.preventDefault(); // Prevent blur
                this.selectItem(index);
            });

            div.addEventListener('mouseenter', () => {
                this.highlightItem(index);
            });

            this.dropdown.appendChild(div);
        });
    }

    selectNext() {
        const newIndex = this.selectedIndex < this.items.length - 1
            ? this.selectedIndex + 1
            : 0;
        this.highlightItem(newIndex);
    }

    selectPrev() {
        const newIndex = this.selectedIndex > 0
            ? this.selectedIndex - 1
            : this.items.length - 1;
        this.highlightItem(newIndex);
    }

    highlightItem(index) {
        // Remove previous highlight
        const items = this.dropdown.querySelectorAll('.autocomplete-item');
        items.forEach(item => item.classList.remove('active'));

        // Add new highlight
        this.selectedIndex = index;
        if (items[index]) {
            items[index].classList.add('active');
            items[index].scrollIntoView({ block: 'nearest' });
        }
    }

    selectCurrent() {
        if (this.selectedIndex >= 0 && this.selectedIndex < this.items.length) {
            this.selectItem(this.selectedIndex);
        }
    }

    selectItem(index) {
        const item = this.items[index];
        if (item) {
            this.input.value = item;
            this.close();

            // Trigger input event for any listeners
            this.input.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }

    open() {
        if (this.items.length > 0) {
            this.dropdown.style.display = 'block';
            this.isOpen = true;
            this.input.setAttribute('aria-expanded', 'true');
        }
    }

    close() {
        this.dropdown.style.display = 'none';
        this.isOpen = false;
        this.selectedIndex = -1;
        this.input.setAttribute('aria-expanded', 'false');
    }
}

// Auto-initialize on DOMContentLoaded if not manually initialized
document.addEventListener('DOMContentLoaded', function() {
    // Only auto-init if not already handled by page script
    if (typeof window.autocompleteInitialized === 'undefined') {
        document.querySelectorAll('[data-autocomplete]').forEach(input => {
            if (!input._autocomplete) {
                input._autocomplete = new Autocomplete(input, input.dataset.autocomplete);
            }
        });
    }
});
