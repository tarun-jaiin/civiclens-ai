(function () {
  "use strict";

  const tileUrl = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}";
  const tileOptions = {
    maxZoom: 19,
    attribution: 'Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; Sources: Esri, TomTom, Garmin, FAO, NOAA, USGS, &copy; OpenStreetMap contributors, and the GIS User Community',
  };
  const defaultCenter = [20.5937, 78.9629];

  function readJson(id) {
    const node = document.getElementById(id);
    if (!node) return [];
    try {
      return JSON.parse(node.textContent);
    } catch (error) {
      console.error(`Unable to read ${id}`, error);
      return [];
    }
  }

  function addReportMarkers(map, reports) {
    const bounds = [];
    reports.forEach((report) => {
      const latitude = Number.parseFloat(report.latitude);
      const longitude = Number.parseFloat(report.longitude);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;

      const marker = window.L.circleMarker([latitude, longitude], {
        radius: 8,
        color: report.status === "RESOLVED" ? "#16856f" : "#2558c9",
        weight: 2,
        fillColor: report.status === "RESOLVED" ? "#4ac6a0" : "#5c8eff",
        fillOpacity: 0.9,
      }).addTo(map);
      const popup = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = report.title || "Civic report";
      const detail = document.createElement("div");
      detail.textContent = `${report.category.replaceAll("_", " ")} · ${report.status.replaceAll("_", " ")}`;
      popup.append(title, detail);
      marker.bindPopup(popup);
      bounds.push([latitude, longitude]);
    });

    if (bounds.length > 1) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 14 });
    else if (bounds.length === 1) map.setView(bounds[0], 14);
  }

  function initReportMap() {
    const element = document.getElementById("report-map");
    if (!element || !window.L) return;

    const map = window.L.map(element, { scrollWheelZoom: false }).setView(defaultCenter, 5);
    window.L.tileLayer(tileUrl, tileOptions).addTo(map);

    const latitudeInput = document.getElementById("id_latitude");
    const longitudeInput = document.getElementById("id_longitude");
    let marker = null;
    const placePin = (latitude, longitude) => {
      if (marker) marker.setLatLng([latitude, longitude]);
      else marker = window.L.marker([latitude, longitude]).addTo(map);
      latitudeInput.value = latitude.toFixed(6);
      longitudeInput.value = longitude.toFixed(6);
    };

    const existingLatitude = Number.parseFloat(latitudeInput && latitudeInput.value);
    const existingLongitude = Number.parseFloat(longitudeInput && longitudeInput.value);
    if (Number.isFinite(existingLatitude) && Number.isFinite(existingLongitude)) {
      placePin(existingLatitude, existingLongitude);
      map.setView([existingLatitude, existingLongitude], 14);
    }

    map.on("click", (event) => placePin(event.latlng.lat, event.latlng.lng));
    const locationButton = document.getElementById("use-location");
    if (locationButton) {
      locationButton.addEventListener("click", () => {
        if (!navigator.geolocation) {
          locationButton.textContent = "Location unavailable";
          return;
        }
        locationButton.disabled = true;
        navigator.geolocation.getCurrentPosition(
          (position) => {
            const point = [position.coords.latitude, position.coords.longitude];
            placePin(point[0], point[1]);
            map.setView(point, 15);
            locationButton.disabled = false;
          },
          (error) => {
            console.warn("Browser location was not available", error);
            locationButton.disabled = false;
            locationButton.textContent = "Location permission denied";
          },
          { enableHighAccuracy: true, timeout: 10000 }
        );
      });
    }
    window.setTimeout(() => map.invalidateSize(), 100);
  }

  function initOverviewMaps() {
    if (!window.L) return;
    [
      ["admin-map", "admin-map-data"],
      ["citizen-map", "citizen-map-data"],
    ].forEach(([mapId, dataId]) => {
      const element = document.getElementById(mapId);
      if (!element) return;
      const reports = readJson(dataId);
      const map = window.L.map(element, { scrollWheelZoom: false }).setView(defaultCenter, 5);
      window.L.tileLayer(tileUrl, tileOptions).addTo(map);
      addReportMarkers(map, reports);
      window.setTimeout(() => map.invalidateSize(), 100);
    });
  }

  function initComplaintDetailMap() {
    const element = document.getElementById("complaint-map");
    if (!element || !window.L) return;
    const latitude = Number.parseFloat(element.dataset.latitude);
    const longitude = Number.parseFloat(element.dataset.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
    const map = window.L.map(element, { scrollWheelZoom: false }).setView([latitude, longitude], 15);
    window.L.tileLayer(tileUrl, tileOptions).addTo(map);
    window.L.marker([latitude, longitude]).addTo(map);
    window.setTimeout(() => map.invalidateSize(), 100);
  }

  function initCharts() {
    if (!window.Chart) return;
    const palette = ["#315bd6", "#22a68a", "#f0a94b", "#e36c61", "#7d74d8", "#49a8c6"];
    [
      ["category-chart", "category-chart-data", "doughnut"],
      ["status-chart", "status-chart-data", "bar"],
    ].forEach(([canvasId, dataId, type]) => {
      const canvas = document.getElementById(canvasId);
      if (!canvas) return;
      const chartData = readJson(dataId);
      new window.Chart(canvas, {
        type,
        data: {
          labels: chartData.labels || [],
          datasets: [{
            data: chartData.values || [],
            backgroundColor: palette,
            borderColor: "#fff",
            borderWidth: type === "doughnut" ? 4 : 0,
            borderRadius: type === "bar" ? 7 : 0,
            hoverOffset: type === "doughnut" ? 8 : 0,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: type === "doughnut" ? "bottom" : "top",
              labels: { usePointStyle: true, boxWidth: 8, padding: 18 },
            },
          },
          scales: type === "bar"
            ? {
                x: { grid: { display: false } },
                y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "rgba(36, 57, 91, .08)" } },
              }
            : {},
        },
      });
    });
  }

  function initAiSuggestion() {
    const button = document.getElementById("ai-suggest");
    const description = document.getElementById("id_description");
    const category = document.getElementById("id_category");
    const output = document.getElementById("ai-suggestion");
    if (!button || !description || !category || !output) return;

    button.addEventListener("click", async () => {
      const text = description.value.trim();
      if (!text) {
        output.textContent = "Add a short description first.";
        return;
      }
      button.disabled = true;
      output.textContent = "Checking the description…";
      try {
        const response = await fetch("/api/ai/predict/", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")?.value || "",
          },
          body: JSON.stringify({ text }),
        });
        if (!response.ok) throw new Error(`Prediction request returned ${response.status}`);
        const data = await response.json();
        const prediction = data.prediction;
        const option = Array.from(category.options).find((item) => item.value === prediction.category);
        if (option) category.value = option.value;
        const confidence = Math.round(prediction.confidence * 100);
        output.textContent = `Suggested: ${option ? option.text : prediction.category} · ${confidence}% confidence${prediction.needs_human_review ? " · please review this suggestion" : ""}.`;
      } catch (error) {
        console.error("Could not get an AI category suggestion", error);
        output.textContent = "The suggestion is unavailable right now. You can still choose a category yourself.";
      } finally {
        button.disabled = false;
      }
    });
  }

  function initProductGuide() {
    const dialog = document.getElementById("guide-dialog");
    const openButton = document.getElementById("guide-open");
    const closeButton = document.getElementById("guide-close");
    const previousButton = document.getElementById("guide-previous");
    const nextButton = document.getElementById("guide-next");
    const copy = document.getElementById("guide-copy");
    const progress = document.getElementById("guide-progress");
    if (!dialog || !openButton || !closeButton || !previousButton || !nextButton || !copy || !progress) return;

    const guides = {
      resident: [
        { target: ".citizen-metrics", text: "Start here to see how many reports you have submitted, which are still open, and which are resolved." },
        { target: "#complaint-form", text: "Describe the issue, choose a category, and add a useful short title. Category suggestions are optional—check them before submitting." },
        { target: "#report-map", text: "Pin the location by clicking the map or using your location. A clear location helps city staff find the issue." },
        { target: ".report-list", text: "Follow each report here. Open a report to see its status, staff updates, and resolution history." },
      ],
      staff: [
        { target: ".admin-metrics", text: "These cards summarize the current queue, including urgent, unassigned, and overdue reports." },
        { target: ".filter-bar", text: "Search and filter the queue to focus on a status or issue category." },
        { target: "#admin-map", text: "Use the map to understand where reports are located. A pin only appears when the resident provides coordinates." },
        { target: ".queue-table", text: "Open a report to review its details and history, then assign a department or update its status. Every change is recorded." },
        { target: "#ai-assistant-link", text: "AI triage offers suggestions, not decisions. Review the report and use your team's policy before acting." },
      ],
      visitor: [
        { target: ".role-cards", text: "Residents can create an account to report local issues and follow their own reports." },
        { target: "#guide-open", text: "City staff sign in with an account provisioned by an administrator. Staff accounts cannot be created through public sign-up." },
      ],
    };
    const steps = guides[document.body.dataset.userRole] || guides.visitor;
    let activeStep = 0;
    let highlighted = null;

    function renderStep() {
      const step = steps[activeStep];
      progress.textContent = `Step ${activeStep + 1} of ${steps.length}`;
      copy.textContent = step.text;
      previousButton.disabled = activeStep === 0;
      nextButton.textContent = activeStep === steps.length - 1 ? "Done" : "Next";
      if (highlighted) highlighted.classList.remove("guide-highlight");
      highlighted = document.querySelector(step.target);
      if (highlighted) {
        highlighted.classList.add("guide-highlight");
        highlighted.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }

    function closeGuide() {
      if (highlighted) highlighted.classList.remove("guide-highlight");
      highlighted = null;
      dialog.close();
      openButton.focus();
    }

    openButton.addEventListener("click", () => {
      activeStep = 0;
      renderStep();
      dialog.showModal();
      nextButton.focus();
    });
    closeButton.addEventListener("click", closeGuide);
    previousButton.addEventListener("click", () => {
      if (activeStep > 0) {
        activeStep -= 1;
        renderStep();
      }
    });
    nextButton.addEventListener("click", () => {
      if (activeStep === steps.length - 1) {
        closeGuide();
        return;
      }
      activeStep += 1;
      renderStep();
    });
    dialog.addEventListener("close", () => {
      if (highlighted) highlighted.classList.remove("guide-highlight");
      highlighted = null;
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initReportMap();
    initOverviewMaps();
    initComplaintDetailMap();
    initCharts();
    initAiSuggestion();
    initProductGuide();
  });
})();
