/**
 * Canvas-based elevation profile chart.
 *
 * Draws an elevation profile for a ski route with:
 * - X axis: cumulative distance
 * - Y axis: elevation in meters
 * - Color-coded segments (slope colors, gray for lifts)
 * - Gradient fill below the line
 * - Y-axis labels and grid lines
 */

class ElevationChart {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        // Colors matching CSS
        this.colors = {
            green: '#22c55e',
            blue: '#3b82f6',
            red: '#ef4444',
            black: '#1f2937',
            lift: '#9ca3af',
        };

        // Handle resize
        this._resizeHandler = () => this._lastData && this.render(this._lastData.profile, this._lastData.steps);
        window.addEventListener('resize', this._resizeHandler);
    }

    /**
     * Render the elevation profile.
     */
    render(profile, steps) {
        if (!profile || profile.length < 2) return;

        // Store for resize
        this._lastData = { profile, steps };

        // Set canvas size for high DPI
        const container = this.canvas.parentElement;
        const dpr = window.devicePixelRatio || 1;
        const width = container.clientWidth;
        const height = container.clientHeight;

        this.canvas.width = width * dpr;
        this.canvas.height = height * dpr;
        this.canvas.style.width = `${width}px`;
        this.canvas.style.height = `${height}px`;

        this.ctx.scale(dpr, dpr);

        // Drawing area with padding for labels
        const padding = { top: 10, right: 10, bottom: 30, left: 48 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;

        // Clear
        this.ctx.clearRect(0, 0, width, height);

        // Data ranges
        const maxDist = profile[profile.length - 1].distance;
        const elevations = profile.map(p => p.elevation);
        const minEle = Math.min(...elevations);
        const maxEle = Math.max(...elevations);
        const eleRange = maxEle - minEle || 100;
        const elePad = eleRange * 0.1;

        const yMin = minEle - elePad;
        const yMax = maxEle + elePad;
        const yRange = yMax - yMin;

        // Coordinate transforms
        const xScale = (dist) => padding.left + (dist / maxDist) * chartW;
        const yScale = (ele) => padding.top + chartH - ((ele - yMin) / yRange) * chartH;

        // Draw grid lines and Y labels
        this._drawGrid(padding, chartW, chartH, yMin, yMax, yRange, xScale, yScale, width);

        // Draw X axis labels
        this._drawXLabels(padding, chartW, chartH, maxDist, xScale, height);

        // Draw filled area under the profile with gradient
        this._drawFilledArea(profile, xScale, yScale, padding, chartH);

        // Draw colored line segments
        this._drawColoredLine(profile, steps, xScale, yScale);

        // Draw node markers
        this._drawNodeMarkers(profile, xScale, yScale);
    }

    _drawGrid(padding, chartW, chartH, yMin, yMax, yRange, xScale, yScale, width) {
        const ctx = this.ctx;

        // Calculate nice grid intervals
        const niceInterval = this._niceInterval(yMax - yMin, 4);
        const startEle = Math.ceil(yMin / niceInterval) * niceInterval;

        ctx.save();
        ctx.strokeStyle = '#e5e7eb';
        ctx.lineWidth = 0.5;
        ctx.fillStyle = '#6b7280';
        ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';

        for (let ele = startEle; ele <= yMax; ele += niceInterval) {
            const y = yScale(ele);
            if (y < padding.top || y > padding.top + chartH) continue;

            // Grid line
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(padding.left + chartW, y);
            ctx.stroke();

            // Label
            ctx.fillText(`${Math.round(ele)}m`, padding.left - 6, y);
        }

        ctx.restore();
    }

    _drawXLabels(padding, chartW, chartH, maxDist, xScale, height) {
        const ctx = this.ctx;
        ctx.save();
        ctx.fillStyle = '#6b7280';
        ctx.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        const y = padding.top + chartH + 8;

        // Start
        ctx.textAlign = 'left';
        ctx.fillText('0', padding.left, y);

        // End
        ctx.textAlign = 'right';
        const totalKm = maxDist >= 1000
            ? `${(maxDist / 1000).toFixed(1)} km`
            : `${Math.round(maxDist)} m`;
        ctx.fillText(totalKm, padding.left + chartW, y);

        // Middle
        if (chartW > 200) {
            ctx.textAlign = 'center';
            const midDist = maxDist / 2;
            const midLabel = midDist >= 1000
                ? `${(midDist / 1000).toFixed(1)} km`
                : `${Math.round(midDist)} m`;
            ctx.fillText(midLabel, xScale(midDist), y);
        }

        ctx.restore();
    }

    _drawFilledArea(profile, xScale, yScale, padding, chartH) {
        const ctx = this.ctx;
        ctx.save();

        ctx.beginPath();
        ctx.moveTo(xScale(profile[0].distance), yScale(profile[0].elevation));

        for (let i = 1; i < profile.length; i++) {
            ctx.lineTo(xScale(profile[i].distance), yScale(profile[i].elevation));
        }

        // Close along bottom
        ctx.lineTo(xScale(profile[profile.length - 1].distance), padding.top + chartH);
        ctx.lineTo(xScale(profile[0].distance), padding.top + chartH);
        ctx.closePath();

        // Gradient fill
        const gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartH);
        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.15)');
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0.02)');
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.restore();
    }

    _drawColoredLine(profile, steps, xScale, yScale) {
        const ctx = this.ctx;
        ctx.save();
        ctx.lineWidth = 2.5;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';

        for (let i = 1; i < profile.length; i++) {
            const prev = profile[i - 1];
            const curr = profile[i];

            // Determine segment color
            let color = this.colors.lift;
            if (curr.type === 'slope' && curr.difficulty) {
                color = this.colors[curr.difficulty] || this.colors.blue;
            } else if (curr.type === 'lift') {
                color = this.colors.lift;
            }

            ctx.strokeStyle = color;
            ctx.beginPath();
            ctx.moveTo(xScale(prev.distance), yScale(prev.elevation));
            ctx.lineTo(xScale(curr.distance), yScale(curr.elevation));
            ctx.stroke();
        }

        ctx.restore();
    }

    _drawNodeMarkers(profile, xScale, yScale) {
        const ctx = this.ctx;
        ctx.save();

        for (const point of profile) {
            if (!point.isNode) continue;

            const x = xScale(point.distance);
            const y = yScale(point.elevation);

            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(x, y, 3.5, 0, Math.PI * 2);
            ctx.fill();

            ctx.strokeStyle = '#374151';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(x, y, 3.5, 0, Math.PI * 2);
            ctx.stroke();
        }

        ctx.restore();
    }

    /**
     * Calculate a nice interval for grid lines.
     */
    _niceInterval(range, targetLines) {
        const rough = range / targetLines;
        const magnitude = Math.pow(10, Math.floor(Math.log10(rough)));
        const residual = rough / magnitude;

        let nice;
        if (residual <= 1.5) nice = 1;
        else if (residual <= 3) nice = 2;
        else if (residual <= 7) nice = 5;
        else nice = 10;

        return nice * magnitude;
    }

    destroy() {
        window.removeEventListener('resize', this._resizeHandler);
    }
}
