/**
 * Main application controller for Ski Navigator.
 *
 * Initializes the app: loads graph data, wires up the UI,
 * and handles the route finding flow.
 */

(function () {
    'use strict';

    let graph = null;
    let ui = null;

    async function init() {
        ui = new SkiUI();

        // Set up elevation chart
        const chart = new ElevationChart(ui.elevationCanvas);
        ui.setElevationChart(chart);

        // Wire up event handlers
        ui.swapBtn.addEventListener('click', () => ui.swapSelections());
        ui.findRouteBtn.addEventListener('click', handleFindRoute);

        // Also trigger on Enter key in selects
        ui.startSelect.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') handleFindRoute();
        });
        ui.endSelect.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') handleFindRoute();
        });

        // Load graph data
        try {
            const response = await fetch('data/graph.json');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const graphData = await response.json();

            graph = new SkiGraph(graphData);

            // Populate dropdowns
            const locations = graph.getSelectableLocations();
            ui.populateDropdowns(locations);

        } catch (err) {
            console.error('Failed to load graph data:', err);
            ui.showError('Failed to load ski area data. Please refresh the page.');
        }
    }

    function handleFindRoute() {
        if (!graph) return;

        const startId = ui.startSelect.value;
        const endId = ui.endSelect.value;

        // Validate selections
        if (!startId) {
            ui.showError('Please select a starting point.');
            return;
        }
        if (!endId) {
            ui.showError('Please select a destination.');
            return;
        }

        // Get excluded colors
        const excludedColors = ui.getExcludedColors();

        // Show loading
        ui.showLoading();

        // Use setTimeout to allow UI to update before computing
        setTimeout(() => {
            try {
                const route = graph.findRoute(startId, endId, excludedColors);

                if (!route) {
                    ui.showError('An unexpected error occurred. Please try again.');
                    return;
                }

                if (route.error === 'same_location') {
                    ui.showError('Start and end are the same location. Please select different points.');
                    return;
                }

                if (route.error === 'no_route') {
                    ui.showError('No route found with current slope filters. Try enabling more slope colors.');
                    return;
                }

                // Render results
                ui.renderRoute(route, graph);

            } catch (err) {
                console.error('Route calculation error:', err);
                ui.showError('Failed to calculate route. Please try different points.');
            }
        }, 50);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
