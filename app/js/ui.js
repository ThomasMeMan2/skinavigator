/**
 * UI Controller for Ski Navigator.
 *
 * Handles DOM manipulation, dropdown population, event handling,
 * route result rendering, and error states.
 */

class SkiUI {
    constructor() {
        // DOM elements
        this.startSelect = document.getElementById('start-select');
        this.endSelect = document.getElementById('end-select');
        this.swapBtn = document.getElementById('swap-btn');
        this.findRouteBtn = document.getElementById('find-route-btn');
        this.loading = document.getElementById('loading');
        this.errorMessage = document.getElementById('error-message');
        this.routeResults = document.getElementById('route-results');
        this.stepsList = document.getElementById('steps-list');
        this.elevationCanvas = document.getElementById('elevation-canvas');

        // Summary elements
        this.summaryTime = document.getElementById('summary-time');
        this.summaryDistance = document.getElementById('summary-distance');
        this.summaryUp = document.getElementById('summary-up');
        this.summaryDown = document.getElementById('summary-down');

        // Filter checkboxes
        this.filterGreen = document.getElementById('filter-green');
        this.filterBlue = document.getElementById('filter-blue');
        this.filterRed = document.getElementById('filter-red');
        this.filterBlack = document.getElementById('filter-black');
    }

    /**
     * Populate both start and end dropdowns with grouped locations.
     */
    populateDropdowns(locations) {
        const groups = [
            { label: 'Stations', items: locations.stations },
            { label: 'Lift Bottoms', items: locations.liftBottoms },
            { label: 'Lift Tops', items: locations.liftTops },
            { label: 'Slope Tops', items: locations.slopeTops },
            { label: 'Slope Bottoms', items: locations.slopeBottoms },
        ];

        for (const select of [this.startSelect, this.endSelect]) {
            select.innerHTML = '';

            const placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = 'Select location...';
            placeholder.disabled = true;
            placeholder.selected = true;
            select.appendChild(placeholder);

            for (const group of groups) {
                if (group.items.length === 0) continue;

                const optgroup = document.createElement('optgroup');
                optgroup.label = group.label;

                for (const item of group.items) {
                    const option = document.createElement('option');
                    option.value = item.nodeId;
                    option.textContent = item.label;
                    optgroup.appendChild(option);
                }

                select.appendChild(optgroup);
            }

            select.disabled = false;
        }

        this.swapBtn.disabled = false;
        this.findRouteBtn.disabled = false;
    }

    /**
     * Get the set of excluded slope colors from the filter checkboxes.
     */
    getExcludedColors() {
        const excluded = new Set();
        if (!this.filterGreen.checked) excluded.add('green');
        if (!this.filterBlue.checked) excluded.add('blue');
        if (!this.filterRed.checked) excluded.add('red');
        if (!this.filterBlack.checked) excluded.add('black');
        return excluded;
    }

    /**
     * Swap start and end selections.
     */
    swapSelections() {
        const temp = this.startSelect.value;
        this.startSelect.value = this.endSelect.value;
        this.endSelect.value = temp;
    }

    /**
     * Show loading state.
     */
    showLoading() {
        this.loading.classList.remove('hidden');
        this.errorMessage.classList.add('hidden');
        this.routeResults.classList.add('hidden');
    }

    /**
     * Hide loading state.
     */
    hideLoading() {
        this.loading.classList.add('hidden');
    }

    /**
     * Show error message.
     */
    showError(message) {
        this.hideLoading();
        this.errorMessage.textContent = message;
        this.errorMessage.classList.remove('hidden');
        this.routeResults.classList.add('hidden');
    }

    /**
     * Render route results.
     */
    renderRoute(route, graph) {
        this.hideLoading();
        this.errorMessage.classList.add('hidden');
        this.routeResults.classList.remove('hidden');

        // Render summary
        this.renderSummary(route.summary);

        // Render steps
        this.renderSteps(route.steps, graph);

        // Render elevation profile
        if (this.elevationChart) {
            this.elevationChart.render(route.elevationProfile, route.steps);
        }

        // Scroll to results
        this.routeResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * Render route summary.
     */
    renderSummary(summary) {
        const hours = Math.floor(summary.totalTime / 60);
        const mins = summary.totalTime % 60;
        this.summaryTime.textContent = hours > 0
            ? `${hours}h ${mins}min`
            : `${mins} min`;

        if (summary.totalDistance >= 1000) {
            this.summaryDistance.textContent = `${(summary.totalDistance / 1000).toFixed(1)} km`;
        } else {
            this.summaryDistance.textContent = `${summary.totalDistance} m`;
        }

        this.summaryUp.textContent = `+${summary.totalUp} m`;
        this.summaryDown.textContent = `-${summary.totalDown} m`;
    }

    /**
     * Render route steps.
     */
    renderSteps(steps, graph) {
        this.stepsList.innerHTML = '';

        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];
            const li = document.createElement('li');
            li.className = 'step-item';

            // Icon
            const icon = document.createElement('div');
            icon.className = 'step-icon';

            if (step.type === 'lift') {
                icon.classList.add('lift');
                icon.textContent = this.getLiftIcon(step.liftType);
            } else {
                icon.classList.add(step.difficulty || 'blue');
                icon.textContent = '\u26F7'; // skier emoji
            }

            // Content
            const content = document.createElement('div');
            content.className = 'step-content';

            // Name and type badge
            const nameRow = document.createElement('div');
            const nameSpan = document.createElement('span');
            nameSpan.className = 'step-name';
            nameSpan.textContent = step.name;
            nameRow.appendChild(nameSpan);

            const typeBadge = document.createElement('span');
            typeBadge.className = 'step-type';
            if (step.type === 'lift') {
                typeBadge.classList.add('lift');
                typeBadge.textContent = this.getLiftTypeName(step.liftType);
            } else {
                typeBadge.classList.add(step.difficulty || 'blue');
                typeBadge.textContent = step.difficulty || 'slope';
            }
            nameRow.appendChild(typeBadge);
            content.appendChild(nameRow);

            // Details
            const details = document.createElement('div');
            details.className = 'step-details';

            // Elevation change
            const eleDetail = document.createElement('span');
            eleDetail.className = 'step-detail';
            if (step.elevationDelta > 0) {
                eleDetail.innerHTML = `<span class="arrow-up">\u2191</span> ${step.elevationDelta}m`;
            } else if (step.elevationDelta < 0) {
                eleDetail.innerHTML = `<span class="arrow-down">\u2193</span> ${Math.abs(step.elevationDelta)}m`;
            } else {
                eleDetail.textContent = '\u2194 flat';
            }
            details.appendChild(eleDetail);

            // Distance
            const distDetail = document.createElement('span');
            distDetail.className = 'step-detail';
            if (step.distance >= 1000) {
                distDetail.textContent = `${(step.distance / 1000).toFixed(1)} km`;
            } else {
                distDetail.textContent = `${step.distance} m`;
            }
            details.appendChild(distDetail);

            // Estimated time
            const timeDetail = document.createElement('span');
            timeDetail.className = 'step-detail';
            timeDetail.textContent = `~${Math.round(step.estimatedMinutes)} min`;
            details.appendChild(timeDetail);

            content.appendChild(details);

            li.appendChild(icon);
            li.appendChild(content);
            this.stepsList.appendChild(li);
        }
    }

    /**
     * Get an icon character for lift type.
     */
    getLiftIcon(liftType) {
        switch (liftType) {
            case 'gondola': return '\uD83D\uDEA0'; // aerial tramway
            case 'cable_car': return '\uD83D\uDEA1'; // aerial tramway
            case 'chair_lift': return '\uD83D\uDEA0';
            case 'drag_lift': return '\u26F7';
            default: return '\uD83D\uDEA0';
        }
    }

    /**
     * Get human-readable lift type name.
     */
    getLiftTypeName(liftType) {
        switch (liftType) {
            case 'gondola': return 'gondola';
            case 'cable_car': return 'cable car';
            case 'chair_lift': return 'chairlift';
            case 'drag_lift': return 'drag lift';
            case 'magic_carpet': return 'carpet';
            default: return 'lift';
        }
    }

    /**
     * Set the elevation chart renderer.
     */
    setElevationChart(chart) {
        this.elevationChart = chart;
    }
}
