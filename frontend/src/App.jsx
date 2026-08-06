import React, { useState, useEffect } from 'react';

export default function App() {
  const [theme, setTheme] = useState(localStorage.getItem('weather-theme') || 'dark');
  const [citiesData, setCitiesData] = useState([]);
  const [forecastData, setForecastData] = useState({});
  const [historyData, setHistoryData] = useState([]);
  const [activeCity, setActiveCity] = useState('Kuala Lumpur');
  const [activeHourIndex, setActiveHourIndex] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const API_BASE = import.meta.env.VITE_API_URL || '';

  // Sync theme class to body
  useEffect(() => {
    document.body.className = `theme-${theme}`;
    localStorage.setItem('weather-theme', theme);
  }, [theme]);

  // Load initial data
  useEffect(() => {
    async function loadData() {
      try {
        // Fetch list of cities
        const citiesRes = await fetch(`${API_BASE}/api/cities`);
        const citiesList = await citiesRes.json();
        setCitiesData(citiesList);

        // Fetch forecast and logs
        await refreshForecastsAndHistory();
      } catch (err) {
        console.error('Failed to initialize dashboard data:', err);
      }
    }
    loadData();
  }, []);

  async function refreshForecastsAndHistory() {
    try {
      const forecastRes = await fetch(`${API_BASE}/api/forecast`);
      const forecastList = await forecastRes.json();
      
      const forecastMap = {};
      forecastList.forEach(item => {
        forecastMap[item.city] = item;
      });
      setForecastData(forecastMap);

      const historyRes = await fetch(`${API_BASE}/api/history`);
      const historyList = await historyRes.json();
      setHistoryData(historyList);
    } catch (err) {
      console.error('Error fetching forecasts/history:', err);
    }
  }

  // City selection
  function handleSelectCity(cityName) {
    setActiveCity(cityName);
    setActiveHourIndex(0); // Reset timeline to first hour of tomorrow
  }

  // WMO codes translator
  function getWmoWeatherDetails(code) {
    if (code === undefined || code === null) {
      return { icon: "☀️", desc: "Clear Sky" };
    }
    if (code === 0) {
      return { icon: "☀️", desc: "Clear Sky" };
    } else if ([1, 2, 3].includes(code)) {
      return { icon: "⛅", desc: "Partly Cloudy" };
    } else if ([45, 48].includes(code)) {
      return { icon: "🌫️", desc: "Foggy" };
    } else if ([51, 53, 55, 56, 57].includes(code)) {
      return { icon: "🌧️", desc: "Tropical Drizzle" };
    } else if ([61, 63, 65, 66, 67].includes(code)) {
      return { icon: "🌧️⛈️", desc: "Heavy Rain" };
    } else if ([71, 73, 75, 77, 85, 86].includes(code)) {
      return { icon: "🌨️", desc: "Cold Precipitation" };
    } else if ([80, 81, 82].includes(code)) {
      return { icon: "🌧️⛈️", desc: "Passing Showers" };
    } else if ([95, 96, 99].includes(code)) {
      return { icon: "⛈️🌩️", desc: "Thunderstorm" };
    } else {
      return { icon: "⛅", desc: "Unsettled" };
    }
  }

  async function triggerForecastFetch() {
    setIsRefreshing(true);
    await refreshForecastsAndHistory();
    setIsRefreshing(false);
  }

  // Active City forecast data
  const activeCityForecast = forecastData[activeCity];
  const hourlyRecords = activeCityForecast?.hourly_records || [];
  const activeHourRecord = hourlyRecords[activeHourIndex];

  // Radial gauge offset calculator
  const probabilityVal = activeHourRecord ? activeHourRecord.probability : 0;
  const strokeOffset = 440 - (440 * probabilityVal);

  return (
    <div className="app-container">
      {/* Sidebar Panel */}
      <aside className="sidebar">
        <div>
          <h1 className="header-title">
            <svg className="icon-svg" viewBox="0 0 24 24">
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
              <circle cx="12" cy="12" r="4" />
            </svg>
            MET-MALAYSIA
          </h1>
          <p className="header-desc">Hobby Hourly Rainfall Forecaster powered by localized Random Forest models.</p>
        </div>

        {/* Theme Selectors */}
        <div className="theme-switcher-wrapper">
          <button 
            className={`theme-btn ${theme === 'dark' ? 'active' : ''}`} 
            onClick={() => setTheme('dark')}
          >
            🌙 Dark
          </button>
          <button 
            className={`theme-btn ${theme === 'light' ? 'active' : ''}`} 
            onClick={() => setTheme('light')}
          >
            ☀️ Light
          </button>
          <button 
            className={`theme-btn ${theme === 'custom' ? 'active' : ''}`} 
            onClick={() => setTheme('custom')}
          >
            🔮 Cyber
          </button>
        </div>

        {/* Sidebar Navigation */}
        <div className="city-list">
          {citiesData.map(city => {
            const cityFc = forecastData[city.name] || {};
            const recs = cityFc.hourly_records || [];
            const anyRain = recs.some(r => r.predicted_rain_next_hour === 1);
            const badgeLabel = anyRain ? 'Rain' : 'Dry';

            return (
              <div 
                key={city.name} 
                className={`city-card ${city.name === activeCity ? 'active' : ''}`}
                onClick={() => handleSelectCity(city.name)}
              >
                <div className="city-info">
                  <h3>{city.name}</h3>
                  <p>Lat: {city.latitude.toFixed(2)}, Lon: {city.longitude.toFixed(2)}</p>
                </div>
                <span className={`badge-prediction ${anyRain ? 'rain' : 'norain'}`}>
                  {badgeLabel}
                </span>
              </div>
            );
          })}
        </div>
      </aside>

      {/* Main Panel Content */}
      <main className="main-panel">
        
        {/* Active Hero Card Display */}
        <div className="hero-forecast" id="heroCard">
          <div className="hero-content">
            <div className="monsoon-badge">
              {activeCityForecast ? activeCityForecast.monsoon_period : '--'}
            </div>
            <h2 className="hero-city-name">
              <span>{activeCity}</span>
              <span className="hero-city-time">
                {activeHourRecord ? new Date(activeHourRecord.forecast_time).toLocaleTimeString('en-SG', { hour: '2-digit', minute: '2-digit', hour12: false }) : '00:00'}
              </span>
            </h2>
            
            <div className="forecast-result-wrapper">
              <p className="forecast-label">Forecast Next Hour</p>
              {activeHourRecord ? (
                <div className={`forecast-outcome ${activeHourRecord.predicted_rain_next_hour === 1 ? 'rain' : 'norain'}`}>
                  {activeHourRecord.predicted_rain_next_hour === 1 ? '🌧️ ' : `${getWmoWeatherDetails(activeHourRecord.weather_code).icon} `}
                  {getWmoWeatherDetails(activeHourRecord.weather_code).desc.toUpperCase()}
                </div>
              ) : (
                <div className="forecast-outcome">No Data Found</div>
              )}
            </div>
          </div>

          {/* Radial probability ring */}
          <div className="gauge-wrapper">
            <svg className="gauge-svg" width="165" height="165" viewBox="0 0 160 160">
              <defs>
                <linearGradient id="neon-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="var(--accent-cyan)" />
                  <stop offset="100%" stopColor="var(--accent-blue)" />
                </linearGradient>
              </defs>
              <circle className="gauge-bg" cx="80" cy="80" r="70" />
              <circle 
                className="gauge-fill" 
                cx="80" 
                cy="80" 
                r="70" 
                style={{ strokeDashoffset: strokeOffset }}
              />
            </svg>
            <div className="gauge-text">
              <span className="gauge-percentage">
                {activeHourRecord ? `${Math.round(activeHourRecord.probability * 100)}%` : '--'}
              </span>
              <span className="gauge-title">Probability</span>
            </div>
          </div>
        </div>

        {/* 24h Area Bar Chart Timeline */}
        <section className="timeline-section">
          <div className="timeline-header">
            <h3 className="section-title">24-Hour Rain Probability Timeline</h3>
          </div>
          <div className="chart-container">
            {hourlyRecords.length > 0 ? (
              hourlyRecords.map((hour, idx) => {
                const wmo = getWmoWeatherDetails(hour.weather_code);
                const probPercent = Math.round(hour.probability * 100);
                const hourStr = new Date(hour.forecast_time).toLocaleTimeString('en-SG', { hour: '2-digit', minute: '2-digit', hour12: false }).split(':')[0];

                return (
                  <div 
                    key={hour.forecast_time}
                    className={`chart-bar-wrapper ${idx === activeHourIndex ? 'active' : ''}`}
                    onClick={() => setActiveHourIndex(idx)}
                  >
                    <div className="chart-tooltip">{wmo.icon} {wmo.desc}</div>
                    <div className="chart-bar-container">
                      <div className="chart-bar" style={{ height: `${probPercent}%` }} />
                    </div>
                    <span className="chart-bar-label">{probPercent}%</span>
                    <span className="chart-bar-time">{hourStr}h</span>
                  </div>
                );
              })
            ) : (
              <div style={{ color: 'var(--text-secondary)', padding: '1.5rem', textAlign: 'center', width: '100%' }}>
                No forecast timeline available.
              </div>
            )}
          </div>
        </section>

        {/* Dials Info Grid */}
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">☀️ Temp Value</span>
            <span className="metric-value">
              {activeHourRecord ? `${activeHourRecord.temperature_2m.toFixed(1)}°C` : '--'}
            </span>
          </div>
          <div className="metric-card">
            <span className="metric-label">💧 Relative Humidity</span>
            <span className="metric-value">
              {activeHourRecord ? `${Math.round(activeHourRecord.relative_humidity_2m)}%` : '--'}
            </span>
          </div>
          <div className="metric-card">
            <span className="metric-label">🌬️ Wind Speed</span>
            <span className="metric-value">
              {activeHourRecord ? `${activeHourRecord.wind_speed_10m.toFixed(1)} km/h (${Math.round(activeHourRecord.wind_direction_10m)}°)` : '--'}
            </span>
          </div>
          <div className="metric-card">
            <span className="metric-label">🎈 Surface Pressure</span>
            <span className="metric-value">
              {activeHourRecord ? `${Math.round(activeHourRecord.surface_pressure)} hPa` : '--'}
            </span>
          </div>
        </div>

        {/* SQLite Logs History Table */}
        <section className="history-section">
          <div className="section-header">
            <h2 className="section-title">Prediction Archives (Last 100 Hours)</h2>
            <button 
              className="refresh-btn" 
              onClick={triggerForecastFetch} 
              disabled={isRefreshing}
            >
              {isRefreshing ? 'Running Predicts...' : 'Run Forecast Update'}
            </button>
          </div>
          
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Forecast Time</th>
                  <th>City</th>
                  <th>Temp (°C)</th>
                  <th>Rain Probability</th>
                  <th>Predicted State</th>
                </tr>
              </thead>
              <tbody>
                {historyData.length > 0 ? (
                  historyData.map(item => (
                    <tr key={item.id}>
                      <td>{item.timestamp}</td>
                      <td>{item.forecast_time}</td>
                      <td style={{ fontWeight: 600 }}>{item.city}</td>
                      <td>{item.temperature_2m.toFixed(1)}°C</td>
                      <td style={{ fontWeight: 600 }}>{Math.round(item.probability * 100)}%</td>
                      <td>
                        <span className={`badge-prediction ${item.predicted_rain_next_hour === 1 ? 'rain' : 'norain'}`}>
                          {item.predicted_rain_next_hour === 1 ? 'Rain' : 'Dry'}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                      No forecast archives found. Click 'Run Forecast Update'.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
