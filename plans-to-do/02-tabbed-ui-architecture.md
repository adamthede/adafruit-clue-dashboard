# Implementation Plan: Tabbed UI Architecture

**Priority:** CRITICAL - Foundation
**Phase:** 1
**Estimated Effort:** 3-4 hours
**Dependencies:** None
**Blocks:** 03-14 (all UI features need tabs)

---

## Overview

Restructure the existing single-page interface into a tabbed architecture that preserves the current "Live Monitor" functionality while providing dedicated spaces for new analysis features. This creates a clean separation between real-time monitoring and historical analysis.

---

## Goals & Objectives

1. **Zero Breaking Changes**: Existing live monitor must work identically
2. **Clean Navigation**: Intuitive tab switching between views
3. **State Preservation**: Each tab maintains its own state
4. **Extensibility**: Easy to add new tabs for future features
5. **Responsive Design**: Tabs work on various window sizes

---

## Architecture

### UI Layout Structure

```
┌────────────────────────────────────────────────────────┐
│  CLUE Environmental Monitor                            │
├────────────────────────────────────────────────────────┤
│  [ Live Monitor ] [ Analysis ] [ Patterns ] [ Export ] │ ← Tab Bar
├────────────────────────────────────────────────────────┤
│                                                        │
│  TAB CONTENT AREA                                     │
│  (Different content based on active tab)              │
│                                                        │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### Tab Definitions

| Tab Name | Description | Priority |
|----------|-------------|----------|
| **Live Monitor** | Current interface (unchanged) | Critical |
| **Analysis** | Statistics, correlations, insights | High |
| **Patterns** | Heatmaps, calendar, daily patterns | High |
| **Export** | Enhanced export with reports | Medium |

---

## File Structure Changes

### Before:
```
/
├── index.html (single page)
├── script.js (all JS logic)
└── gateway_webview.py
```

### After:
```
/
├── index.html (tab structure + Live Monitor content)
├── tabs/
│   ├── tab_analysis.html (NEW - Analysis tab content)
│   ├── tab_patterns.html (NEW - Patterns tab content)
│   └── tab_export.html (NEW - Export tab content)
├── js/
│   ├── script.js (renamed from root, Live Monitor logic)
│   ├── tab_manager.js (NEW - tab switching logic)
│   ├── analysis.js (NEW - for Analysis tab)
│   ├── patterns.js (NEW - for Patterns tab)
│   └── export.js (NEW - for Export tab)
├── css/
│   └── styles.css (NEW - extracted from inline styles)
└── gateway_webview.py (minimal changes)
```

---

## Technical Specifications

### HTML Structure (index.html)

```html
<!DOCTYPE html>
<html>
<head>
    <title>CLUE Environmental Monitor</title>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="css/styles.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/moment@2.29.1/moment.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-moment@1.0.0/dist/chartjs-adapter-moment.min.js"></script>
</head>
<body>
    <!-- Tab Navigation Bar -->
    <nav class="tab-nav">
        <button class="tab-button active" data-tab="live">Live Monitor</button>
        <button class="tab-button" data-tab="analysis">Analysis</button>
        <button class="tab-button" data-tab="patterns">Patterns</button>
        <button class="tab-button" data-tab="export">Export</button>
    </nav>

    <!-- Tab Content Containers -->
    <div id="tab-live" class="tab-content active">
        <!-- EXISTING CONTENT - MOVED HERE UNCHANGED -->
        <!-- All current HTML from index.html -->
    </div>

    <div id="tab-analysis" class="tab-content hidden">
        <!-- Will be populated from tabs/tab_analysis.html -->
        <div id="analysis-container"></div>
    </div>

    <div id="tab-patterns" class="tab-content hidden">
        <!-- Will be populated from tabs/tab_patterns.html -->
        <div id="patterns-container"></div>
    </div>

    <div id="tab-export" class="tab-content hidden">
        <!-- Will be populated from tabs/tab_export.html -->
        <div id="export-container"></div>
    </div>

    <!-- Scripts -->
    <script src="js/tab_manager.js"></script>
    <script src="js/script.js"></script>
    <script src="js/analysis.js"></script>
    <script src="js/patterns.js"></script>
    <script src="js/export.js"></script>
</body>
</html>
```

### CSS (css/styles.css)

```css
/* Extract all inline styles from current index.html */
/* Plus new tab-specific styles */

/* Tab Navigation */
.tab-nav {
    display: flex;
    background-color: #2c3e50;
    padding: 0;
    margin: 0;
    border-bottom: 2px solid #34495e;
}

.tab-button {
    flex: 1;
    padding: 15px 20px;
    background-color: #34495e;
    color: #ecf0f1;
    border: none;
    cursor: pointer;
    font-size: 16px;
    transition: background-color 0.3s;
    border-right: 1px solid #2c3e50;
}

.tab-button:hover {
    background-color: #3d5770;
}

.tab-button.active {
    background-color: #2980b9;
    font-weight: bold;
}

/* Tab Content */
.tab-content {
    display: none;
    padding: 20px;
    animation: fadeIn 0.3s;
}

.tab-content.active {
    display: block;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* Preserve all existing styles */
/* ... copy from inline styles in current index.html ... */
```

### JavaScript - Tab Manager (js/tab_manager.js)

```javascript
/**
 * Tab Manager - Handles tab switching and state management
 */
class TabManager {
    constructor() {
        this.activeTab = 'live';
        this.tabs = ['live', 'analysis', 'patterns', 'export'];
        this.tabState = {}; // Store state for each tab
        this.init();
    }

    init() {
        // Attach click handlers to tab buttons
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Initialize tab content loaders
        this.initTabLoaders();

        // Restore last active tab from localStorage
        const lastTab = localStorage.getItem('lastActiveTab');
        if (lastTab && this.tabs.includes(lastTab)) {
            this.switchTab(lastTab);
        }
    }

    switchTab(tabName) {
        if (!this.tabs.includes(tabName)) {
            console.error(`Invalid tab: ${tabName}`);
            return;
        }

        // Save state of current tab
        this.saveTabState(this.activeTab);

        // Hide all tabs
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });

        // Deactivate all buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });

        // Show selected tab
        document.getElementById(`tab-${tabName}`).classList.add('active');
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update active tab
        this.activeTab = tabName;

        // Save to localStorage
        localStorage.setItem('lastActiveTab', tabName);

        // Trigger tab activation event
        this.onTabActivated(tabName);

        // Restore tab state
        this.restoreTabState(tabName);
    }

    saveTabState(tabName) {
        // Hook for saving tab-specific state
        // Each tab's JS can override this
        const event = new CustomEvent('tab-deactivated', { detail: { tabName } });
        window.dispatchEvent(event);
    }

    restoreTabState(tabName) {
        // Hook for restoring tab-specific state
        const event = new CustomEvent('tab-activated', { detail: { tabName } });
        window.dispatchEvent(event);
    }

    onTabActivated(tabName) {
        // Lazy load tab content if not already loaded
        if (tabName === 'analysis' && !window.analysisTabInitialized) {
            this.loadAnalysisTab();
        } else if (tabName === 'patterns' && !window.patternsTabInitialized) {
            this.loadPatternsTab();
        } else if (tabName === 'export' && !window.exportTabInitialized) {
            this.loadExportTab();
        }
    }

    loadAnalysisTab() {
        // Placeholder - will be implemented by analysis.js
        if (typeof initializeAnalysisTab === 'function') {
            initializeAnalysisTab();
            window.analysisTabInitialized = true;
        }
    }

    loadPatternsTab() {
        // Placeholder - will be implemented by patterns.js
        if (typeof initializePatternsTab === 'function') {
            initializePatternsTab();
            window.patternsTabInitialized = true;
        }
    }

    loadExportTab() {
        // Placeholder - will be implemented by export.js
        if (typeof initializeExportTab === 'function') {
            initializeExportTab();
            window.exportTabInitialized = true;
        }
    }

    getActiveTab() {
        return this.activeTab;
    }
}

// Initialize on page load
let tabManager;
window.addEventListener('DOMContentLoaded', () => {
    tabManager = new TabManager();
});
```

---

## Integration Points

### 1. Modify gateway_webview.py

**Minimal changes needed:**

```python
# In main() or window creation
window = webview.create_window(
    'CLUE Environmental Monitor',
    'index.html',  # Still points to same file
    js_api=api,
    width=1400,    # Slightly wider for tabs
    height=900
)
```

**No other changes required** - all tab switching happens client-side.

### 2. Migrate existing index.html content

**Steps:**
1. Create new index.html with tab structure
2. Move ALL existing HTML content into `<div id="tab-live">`
3. Extract inline styles to `css/styles.css`
4. Move `script.js` to `js/script.js`
5. Test that Live Monitor tab works identically

### 3. Create placeholder tabs

**tabs/tab_analysis.html:**
```html
<div class="analysis-placeholder">
    <h2>Analysis Dashboard</h2>
    <p>Coming soon: Statistics, correlations, and insights</p>
</div>
```

**tabs/tab_patterns.html:**
```html
<div class="patterns-placeholder">
    <h2>Pattern Analysis</h2>
    <p>Coming soon: Heatmaps, calendar view, and trends</p>
</div>
```

**tabs/tab_export.html:**
```html
<div class="export-placeholder">
    <h2>Enhanced Export</h2>
    <p>Coming soon: Reports, summaries, and advanced exports</p>
</div>
```

---

## Implementation Steps

### Step 1: Create directory structure
```bash
mkdir -p js css tabs
```

### Step 2: Extract and reorganize existing code
1. Create `css/styles.css` - copy all `<style>` content from index.html
2. Copy `script.js` to `js/script.js`
3. Update paths in index.html

### Step 3: Create tab navigation HTML
1. Add tab bar to index.html
2. Wrap existing content in `<div id="tab-live">`
3. Add empty divs for other tabs

### Step 4: Create tab_manager.js
1. Implement TabManager class as specified above
2. Add event listeners for tab switching
3. Implement lazy loading hooks

### Step 5: Create placeholder tabs
1. Create minimal HTML for each tab
2. Create minimal JS files (analysis.js, patterns.js, export.js)
3. Each just exports an initialization function

### Step 6: Test thoroughly
1. Verify Live Monitor tab works identically to before
2. Test tab switching
3. Verify localStorage persistence
4. Check for any JavaScript errors

### Step 7: Update paths in gateway_webview.py if needed
1. Ensure webview can access js/ and css/ directories
2. Test application launch

---

## Success Criteria

✅ **Functional Requirements:**
- [ ] Live Monitor tab displays exactly as before
- [ ] Can switch between all tabs smoothly
- [ ] Tab switching has no errors in console
- [ ] Last active tab remembered on reload
- [ ] All existing functionality (connect, export, etc.) works in Live Monitor tab

✅ **Visual Requirements:**
- [ ] Tab bar looks professional and integrated
- [ ] Active tab clearly highlighted
- [ ] Smooth transitions between tabs
- [ ] Responsive to window resizing
- [ ] Consistent styling across tabs

✅ **Technical Requirements:**
- [ ] No JavaScript errors
- [ ] Clean separation of concerns (each tab's JS in separate file)
- [ ] CSS extracted from HTML
- [ ] File structure organized logically
- [ ] Code is documented

---

## Testing Strategy

### Manual Testing Checklist

**Live Monitor Tab:**
1. [ ] Port selection works
2. [ ] Connect/Disconnect works
3. [ ] Live chart updates in real-time
4. [ ] Data table populates
5. [ ] Export buttons function
6. [ ] Time range selector works
7. [ ] Capture interval setting works
8. [ ] Status indicators update

**Tab Switching:**
1. [ ] Click each tab button
2. [ ] Verify content changes
3. [ ] Return to Live Monitor - verify state preserved
4. [ ] Reload page - verify last tab restored
5. [ ] Switch tabs while connected - no disruption to serial

**Browser Console:**
1. [ ] Check for JavaScript errors
2. [ ] Verify console.log messages from tab switching
3. [ ] Test in different browsers (Chrome, Safari, Firefox)

---

## Migration Guide for Existing Code

**For future implementers adding features to tabs:**

1. **Analysis Tab Features** → Put in `js/analysis.js`
2. **Patterns Tab Features** → Put in `js/patterns.js`
3. **Live Monitor Enhancements** → Add to `js/script.js`

**To add content to a tab:**

```javascript
// In js/analysis.js
function initializeAnalysisTab() {
    const container = document.getElementById('analysis-container');

    // Load HTML content
    container.innerHTML = `
        <h2>Analysis Dashboard</h2>
        <div id="stats-cards"></div>
        <div id="correlation-chart"></div>
    `;

    // Initialize functionality
    loadStatistics();
    setupEventListeners();
}

// Tab manager will call this on first activation
window.initializeAnalysisTab = initializeAnalysisTab;
```

---

## Performance Considerations

**Lazy Loading:**
- Only load tab content when first accessed
- Reduces initial page load time
- Improves memory usage

**State Management:**
- Each tab saves/restores its own state
- Prevents data loss when switching tabs
- Use `sessionStorage` for temporary state
- Use `localStorage` for persistent preferences

**Chart Management:**
- Destroy charts when tab is deactivated (optional)
- Recreate when tab is reactivated
- Prevents memory leaks from multiple Chart.js instances

---

## Error Handling

**Missing Tab Content:**
```javascript
onTabActivated(tabName) {
    try {
        if (tabName === 'analysis' && !window.analysisTabInitialized) {
            this.loadAnalysisTab();
        }
    } catch (error) {
        console.error(`Failed to load ${tabName} tab:`, error);
        alert(`Error loading tab. Please refresh the page.`);
    }
}
```

**Invalid Tab Names:**
```javascript
switchTab(tabName) {
    if (!this.tabs.includes(tabName)) {
        console.error(`Invalid tab: ${tabName}`);
        return; // Fail gracefully
    }
    // ... proceed
}
```

---

## Code Review Checklist

Before marking complete:
- [ ] All existing Live Monitor functionality works
- [ ] No hardcoded paths
- [ ] CSS properly extracted
- [ ] JavaScript modularized
- [ ] Tab switching is smooth (no flicker)
- [ ] Browser console has no errors
- [ ] Works in macOS native webview
- [ ] Code is commented
- [ ] File structure is clean

---

## Future Enhancements

**Post-MVP:**
- Add tab badges (e.g., "Analysis (3 alerts)")
- Keyboard shortcuts (Cmd+1, Cmd+2, etc.)
- Tab reordering (drag-and-drop)
- Tab-specific toolbars
- Breadcrumb navigation for sub-sections
- Dark mode toggle

---

## Notes for Implementation Agent

**Critical Path:**
1. Don't break Live Monitor - test after EVERY change
2. Extract CSS carefully - test styles render correctly
3. Ensure pywebview can serve files from subdirectories
4. Test tab switching doesn't interfere with serial connection

**Common Pitfalls:**
- Forgetting to update script src paths
- CSS selectors breaking when restructuring HTML
- Event listeners not working after DOM restructure
- localStorage quota exceeded (unlikely but possible)

**Quick Validation:**
After implementing, run through this 30-second test:
1. Launch app
2. Click each tab → Should switch smoothly
3. Connect to CLUE on Live Monitor tab
4. Switch to Analysis tab
5. Switch back to Live Monitor
6. Verify chart still updating
✅ If all works → Success!

---

**Questions?** The key principle: **Don't break Live Monitor**. Everything else is additive. When in doubt, preserve existing behavior.
