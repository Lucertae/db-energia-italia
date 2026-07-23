# Seismic Monitor

A real-time, interactive 3D globe visualization of global earthquake activity, built with React and Three.js. It pulls live data directly from the USGS GeoJSON feed, processes it using Web Workers, and renders thousands of seismic events smoothly onto a high-performance WebGL globe.

I built this because I wanted a hands-on project that covers complex 3D rendering, efficient data processing with Web Workers, and building a clean, modern UI overlay in one app. The architecture handles real-time streams and renders them without dropping frames, similar to what you'd see in a production-grade data visualization tool.

Built by Aaron Murillo

![Dashboard](src/assets/image/dashboard.jpg)

### What It Does
The app continuously polls the United States Geological Survey (USGS) for earthquake data. You can toggle the time range between the last 24 hours, the last 7 days, or the last 30 days. A background Web Worker parses the incoming GeoJSON, runs the coordinate math, and packages it up for the GPU so the main thread stays entirely unblocked.

The dashboard shows an activity panel on the left for a quick read on total events, largest magnitude, deepest quake, and the most active region. On the right, a live event feed streams in recent earthquakes. Everything updates dynamically as new data arrives from the USGS.

![Pipeline Detail](src/assets/image/detail.jpg)

Clicking into any earthquake in the feed or on the globe opens a detail view. You get stats like magnitude, depth, exact coordinates, and how many people reported feeling the quake. There's also a timeline showing when it happened and a direct link to the official USGS event page.

### Features
- **Live 3D Globe**: Rendered with Three.js and React Three Fiber, featuring tectonic plate boundaries, atmospheric scattering, and smooth orbital controls.
- **Real-Time Data**: Streams live directly from the USGS API.
- **Time-Lapse Playback**: Controls at the bottom let you scrub through recent seismic history at various speeds to see how events unfolded over time.
- **Dynamic Filtering**: Filter the visible earthquakes by magnitude, depth, and time range on the fly.
- **Performance Optimized**: Uses Web Workers for heavy data parsing and instanced rendering to handle thousands of data points without dropping frames.
- **Interactive UI**: Custom-built, responsive glassmorphism interface that overlays the canvas cleanly on both desktop and mobile.

### Tech Stack
- **Frontend**: React 18, Vite
- **3D Rendering**: Three.js, React Three Fiber, React Three Drei, React Three Postprocessing
- **State Management**: Zustand
- **Animations**: Framer Motion
- **Data Source**: USGS GeoJSON Feed

### Project Structure
```text
src/
  components/
    Globe/          # 3D Canvas, Shaders, Instanced meshes, Camera
    HUD/            # UI Panels (Stats, Event Feed, Filters, Playback)
    UI/             # Reusable UI components (GlassPanel, Badges, Modals)
  hooks/            # Custom React hooks (Data fetching loop)
  store/            # Zustand state management (UI state, Earthquake data)
  utils/            # Math, formatters, map generation
  workers/          # Web Workers for offloading data processing
  shaders/          # Custom WebGL Vertex/Fragment shaders
  App.jsx           # Main layout and composition
  index.css         # Global styling and variables
```

### Getting Started

```bash
# Clone the repo
git clone https://github.com/AaronMurillo01/Real-Time-Earthquake-Globe.git
cd Real-Time-Earthquake-Globe

# Install dependencies
npm install

# Run the development server
npm run dev
```

Open `http://localhost:5173` in your browser. The app will immediately begin fetching the last 24 hours of seismic activity and plotting it on the globe.

### License
MIT
