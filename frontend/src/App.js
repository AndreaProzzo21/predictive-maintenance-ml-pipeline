import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const API_URL = "http://3.69.167.220:8080/api/v1/status";
const ITEMS_PER_PAGE = 15;

function App() {
  const [pumps, setPumps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedId, setExpandedId] = useState(null); // Stato per la riga espansa

  const stats = {
    total: pumps.length,
    broken: pumps.filter(p => p.state === 'BROKEN').length,
    faulty: pumps.filter(p => p.state === 'FAULTY').length,
    warning: pumps.filter(p => p.state === 'WARNING').length,
    avgHealth: pumps.length > 0 
      ? (pumps.reduce((acc, p) => acc + (p.health_score || 0), 0) / pumps.length).toFixed(1) 
      : 0
  };

  const fetchData = useCallback(async () => {
    try {
      const url = filter === 'ALL' ? API_URL : `${API_URL}?state=${filter}`;
      const response = await axios.get(url);
      const sortedPumps = response.data.pumps.sort((a, b) =>
        a.device_id.localeCompare(b.device_id, undefined, { numeric: true })
      );
      setPumps(sortedPumps);
      setLoading(false);
    } catch (error) {
      console.error("Fetch error:", error);
    }
  }, [filter]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const indexOfLastItem = currentPage * ITEMS_PER_PAGE;
  const indexOfFirstItem = indexOfLastItem - ITEMS_PER_PAGE;
  const currentPumps = pumps.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(pumps.length / ITEMS_PER_PAGE);

  const handleFilterChange = (newFilter) => {
    setFilter(newFilter);
    setCurrentPage(1);
    setExpandedId(null);
  };

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="container">
      <header className="header">
        <div className="title-section">
          <h1>Pumps Health Monitoring Dashboard</h1>
          <span className="live-indicator">LIVE SYSTEM</span>
        </div>
        <div className="api-info">Node: {API_URL}</div>
      </header>

      <div className="stats-container">
        <div className="stat-card">
          <span className="stat-label">TOTAL ASSETS</span>
          <span className="stat-value">{stats.total}</span>
        </div>
        <div className="stat-card warning">
          <span className="stat-label">WARNINGS</span>
          <span className="stat-value">{stats.warning}</span>
        </div>
        <div className="stat-card faulty">
          <span className="stat-label">FAULTY</span>
          <span className="stat-value">{stats.faulty}</span>
        </div>
        <div className="stat-card broken">
          <span className="stat-label">BROKEN</span>
          <span className="stat-value">{stats.broken}</span>
        </div>
        <div className="stat-card health">
          <span className="stat-label">AVG HEALTH</span>
          <span className="stat-value">{stats.avgHealth}%</span>
        </div>
      </div>

      <div className="filter-bar">
        {['ALL', 'HEALTHY', 'WARNING', 'FAULTY', 'BROKEN'].map((f) => (
          <button 
            key={f} 
            className={`filter-chip ${filter === f ? 'active' : ''}`}
            onClick={() => handleFilterChange(f)}
          >
            {f}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="status-msg">Initializing stream...</div>
      ) : (
        <>
          <div className="monitor-grid">
            <div className="grid-header">
              <span>DEVICE ID</span>
              <span>HEALTH STATUS</span>
              <span>TEMP</span>
              <span>VIBRATION</span>
              <span>STATUS</span>
            </div>

            {currentPumps.map((pump) => (
              <React.Fragment key={pump.device_id}>
                {/* Riga principale cliccabile */}
                <div 
                  className={`pump-row ${expandedId === pump.device_id ? 'expanded' : ''}`} 
                  onClick={() => toggleExpand(pump.device_id)}
                >
                  <span className="device-id">{pump.device_id}</span>
                  <div className="health-column">
                    <span className="value">{pump.health_score?.toFixed(1)}%</span>
                    <div className="health-bar-bg">
                      <div 
                        className={`health-bar-fill ${pump.state?.toLowerCase()}`} 
                        style={{ width: `${pump.health_score}%` }}
                      ></div>
                    </div>
                  </div>
                  <span className="value">{pump.temperature?.toFixed(1)}°C</span>
                  <span className="value">{pump.vibration_rms?.toFixed(2)} mm/s</span>
                  <div className="status-cell">
                    <div className={`status-dot ${pump.state?.toLowerCase()}`}></div>
                    <span className="status-text">{pump.state}</span>
                  </div>
                </div>

                {/* Pannello di dettaglio condizionale */}
                {expandedId === pump.device_id && (
                  <div className="detail-panel">
                    <div className="detail-grid">
                      <div className="detail-item">
                        <span className="detail-label">Current (Ampere)</span>
                        <span className="detail-value">{pump.current?.toFixed(2)} A</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Pressure</span>
                        <span className="detail-value">{pump.pressure?.toFixed(2)} Bar</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Vibration X</span>
                        <span className="detail-value">{pump.vibration_x?.toFixed(2)}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Vibration Y</span>
                        <span className="detail-value">{pump.vibration_y?.toFixed(2)}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Vibration Z</span>
                        <span className="detail-value">{pump.vibration_z?.toFixed(2)}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Last Maintenance</span>
                        <span className="detail-value">{pump.last_maintenance || 'N/A'}</span>
                      </div>
                    </div>
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button 
                disabled={currentPage === 1} 
                onClick={() => setCurrentPage(prev => prev - 1)}
                className="pag-btn"
              >PREVIOUS</button>
              <span className="pag-info">Page {currentPage} of {totalPages}</span>
              <button 
                disabled={currentPage === totalPages} 
                onClick={() => setCurrentPage(prev => prev + 1)}
                className="pag-btn"
              >NEXT</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default App;