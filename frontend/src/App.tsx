import { useState, useEffect } from 'react';
import { 
  Activity, 
  Map as MapIcon, 
  Cpu, 
  Play, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw, 
  TrendingUp, 
  Clock, 
  Users, 
  MapPin, 
  Eye, 
  Calendar,
  Building,
  Home,
  Shield,
  Truck
} from 'lucide-react';
import './App.css';
import { RoadNetworkMap } from './RoadNetworkMap';

interface Intersection {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
}

interface Road {
  id: string;
  name: string;
  start_node: string;
  end_node: string;
  length_meters: number;
  capacity: number;
  speed_limit_kmh: number;
  road_type: string;
  availability: number;
  current_volume: number;
  criticality: number;
}

interface Facility {
  id: string;
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  nearest_node: string;
}

interface PopulationZone {
  id: string;
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  population: number;
  nearest_node: string;
}

interface TransitRoute {
  id: string;
  name: string;
  stops_sequence: string[];
  road_sequence: string[];
}

interface CityData {
  intersections: Intersection[];
  roads: Road[];
  facilities: Facility[];
  population_zones: PopulationZone[];
  transit_routes: TransitRoute[];
}

interface SimulationMetrics {
  average_travel_time_minutes: number;
  max_congestion_ratio: number;
  congested_roads_count: number;
  network_efficiency: number;
  failed_commutes_count: number;
}

interface ActiveScenario {
  scenario_id: string;
  simulation_id: string;
  metrics: SimulationMetrics;
  road_metrics: Record<string, {
    volume: number;
    travel_time_seconds: number;
    congestion_ratio: number;
    availability: number;
  }>;
}

interface CandidatePlan {
  plan_id: string;
  name: string;
  description: string;
  metrics: SimulationMetrics;
}

interface OptimizationData {
  optimization_id: string;
  candidate_plans: CandidatePlan[];
  recommended_plan_id: string;
  narrative: string;
}

function App() {
  const [activeTab, setActiveTab] = useState<'digital-twin' | 'simulator' | 'optimizer'>('digital-twin');
  const [cityData, setCityData] = useState<CityData | null>(null);
  const [scenariosHistory, setScenariosHistory] = useState<any[]>([]);
  const [activeScenario, setActiveScenario] = useState<ActiveScenario | null>(null);
  const [optimizationData, setOptimizationData] = useState<OptimizationData | null>(null);
  
  // Selection states
  const [selectedRoad, setSelectedRoad] = useState<Road | null>(null);
  const [selectedIntersection, setSelectedIntersection] = useState<Intersection | null>(null);
  const [selectedFacility, setSelectedFacility] = useState<Facility | null>(null);
  const [selectedZone, setSelectedZone] = useState<PopulationZone | null>(null);
  
  // Form states
  const [formType, setFormType] = useState<string>('ROAD_CLOSURE');
  const [formTarget, setFormTarget] = useState<string>('');
  const [formSurgeFactor, setFormSurgeFactor] = useState<number>(1.8);
  const [formSpeedReduction, setFormSpeedReduction] = useState<number>(0.35);
  
  // Loaders
  const [loading, setLoading] = useState<boolean>(true);
  const [simulationLoading, setSimulationLoading] = useState<boolean>(false);
  const [optimizationLoading, setOptimizationLoading] = useState<boolean>(false);
  const [apiConfig, setApiConfig] = useState<any>({ db_connected: false, ai_mode: 'fallback' });

  // Fetch baseline city structure
  const fetchCityData = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/city');
      const json = await res.json();
      if (json.success) {
        setCityData(json.data);
      }
    } catch (e) {
      console.error('Failed to fetch city data', e);
    }
  };

  // Fetch scenarios list
  const fetchScenariosHistory = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/scenarios');
      const json = await res.json();
      if (json.success) {
        setScenariosHistory(json.data);
        
        // If there are scenarios, set the latest one as active scenario
        if (json.data.length > 0 && !activeScenario) {
          const latestScen = json.data[0];
          // We can fetch details if needed, or we just leave it to user interactions
        }
      }
    } catch (e) {
      console.error('Failed to fetch scenarios', e);
    }
  };

  // Fetch health/configs
  const fetchHealth = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/health');
      const json = await res.json();
      if (json.success) {
        setApiConfig(json.data);
      }
    } catch (e) {
      console.error('Health check failed', e);
    }
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await fetchHealth();
      await fetchCityData();
      await fetchScenariosHistory();
      setLoading(false);
    };
    init();
  }, []);

  // Sync selected item details when cityData refreshes
  useEffect(() => {
    if (selectedRoad && cityData) {
      const updated = cityData.roads.find(r => r.id === selectedRoad.id);
      if (updated) setSelectedRoad(updated);
    }
  }, [cityData]);


  // Create & run traffic simulation
  const handleLaunchScenario = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTarget && formType !== 'WEATHER_EVENT') {
      alert('Please select a target entity for this scenario.');
      return;
    }
    
    setSimulationLoading(true);
    setOptimizationData(null); // Clear previous optimizations
    
    const params = formType === 'TRAFFIC_SURGE' 
      ? { surge_factor: formSurgeFactor }
      : formType === 'WEATHER_EVENT' 
      ? { speed_reduction_ratio: formSpeedReduction }
      : {};
      
    try {
      const res = await fetch('http://127.0.0.1:8000/api/scenarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: formType,
          target_entity_id: formTarget,
          parameters: params
        })
      });
      const json = await res.json();
      if (json.success) {
        setActiveScenario(json.data);
        await fetchCityData();
        await fetchScenariosHistory();
        setActiveTab('digital-twin'); // Jump to map to see results
      }
    } catch (e) {
      alert('Failed to run simulation. Check if backend is active.');
    } finally {
      setSimulationLoading(false);
    }
  };

  // Run AI Optimization
  const handleRunOptimization = async () => {
    if (!activeScenario) return;
    setOptimizationLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/simulations/${activeScenario.simulation_id}/optimize`, {
        method: 'POST'
      });
      const json = await res.json();
      if (json.success) {
        setOptimizationData(json.data);
        setActiveTab('optimizer');
      }
    } catch (e) {
      alert('Failed to run optimizer.');
    } finally {
      setOptimizationLoading(false);
    }
  };

  // Reset the twin system
  const handleReset = async () => {
    if (!confirm('Are you sure you want to reset the system? All active scenarios and metrics will be cleared.')) return;
    try {
      const res = await fetch('http://127.0.0.1:8000/api/system/reset', { method: 'POST' });
      const json = await res.json();
      if (json.success) {
        setActiveScenario(null);
        setOptimizationData(null);
        setSelectedRoad(null);
        setSelectedIntersection(null);
        setSelectedFacility(null);
        setSelectedZone(null);
        await fetchCityData();
        await fetchScenariosHistory();
        setActiveTab('digital-twin');
      }
    } catch (e) {
      alert('Failed to reset system.');
    }
  };

  // Helper to toggle road blocks from the drawer
  const handleToggleRoadAvailability = async (roadId: string, currentAvail: number) => {
    setSimulationLoading(true);
    try {
      // Toggle works by creating a ROAD_CLOSURE scenario or resetting it
      if (currentAvail === 1) {
        const res = await fetch('http://127.0.0.1:8000/api/scenarios', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'ROAD_CLOSURE',
            target_entity_id: roadId,
            parameters: {}
          })
        });
        const json = await res.json();
        if (json.success) {
          setActiveScenario(json.data);
          await fetchCityData();
          await fetchScenariosHistory();
        }
      } else {
        // To restore a road, we currently reset the system
        await handleReset();
      }
    } catch (e) {
      alert('Failed to toggle road status.');
    } finally {
      setSimulationLoading(false);
    }
  };

  const getCongestionColor = (ratio: number, availability: number) => {
    if (availability === 0) return '#64748b'; // Muted slate gray for closed
    if (ratio <= 0.3) return '#10b981'; // Green
    if (ratio <= 0.7) return '#f59e0b'; // Yellow
    if (ratio <= 0.95) return '#f97316'; // Orange
    return '#f43f5e'; // Red
  };

  const getCongestionLabel = (ratio: number, availability: number) => {
    if (availability === 0) return 'CLOSED';
    if (ratio <= 0.3) return 'Low Traffic';
    if (ratio <= 0.7) return 'Moderate Traffic';
    if (ratio <= 0.95) return 'Heavy Congestion';
    return 'Gridlock Risk';
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: '16px', backgroundColor: '#070a13' }}>
        <Activity className="brand-logo" size={48} style={{ animation: 'spin 2s linear infinite' }} />
        <h2 style={{ fontFamily: 'Outfit', fontWeight: 500 }}>Synchronizing Digital Twin...</h2>
      </div>
    );
  }

  // Aggregate current metrics
  const displayMetrics = activeScenario ? activeScenario.metrics : {
    average_travel_time_minutes: 4.25,
    max_congestion_ratio: 0.5,
    congested_roads_count: 0,
    network_efficiency: 98.5,
    failed_commutes_count: 0
  };

  return (
    <div className="app-container">
      {/* Sidebar Section */}
      <aside className="sidebar">
        <div className="brand-section">
          <Activity className="brand-logo" size={28} />
          <span className="brand-title">CivicTwin v1.0</span>
        </div>
        
        <nav className="nav-menu">
          <button 
            className={`nav-item ${activeTab === 'digital-twin' ? 'active' : ''}`}
            onClick={() => setActiveTab('digital-twin')}
          >
            <MapIcon size={18} />
            <span>Digital Twin Map</span>
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'simulator' ? 'active' : ''}`}
            onClick={() => setActiveTab('simulator')}
          >
            <Play size={18} />
            <span>Scenario Simulator</span>
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'optimizer' ? 'active' : ''}`}
            onClick={() => setActiveTab('optimizer')}
            disabled={!activeScenario}
            style={{ opacity: activeScenario ? 1 : 0.5 }}
          >
            <Cpu size={18} />
            <span>AI Traffic Optimizer</span>
          </button>
        </nav>
        
        <div className="sidebar-footer">
          <div className="system-status">
            <div className="status-row">
              <span className="status-label">Database</span>
              <span className="status-value">
                <span className={`dot ${apiConfig.db_connected ? 'green' : 'red'}`} />
                {apiConfig.db_connected ? 'Online' : 'Offline'}
              </span>
            </div>
            <div className="status-row">
              <span className="status-label">AI Analysis Mode</span>
              <span className="status-value" style={{ color: apiConfig.ai_configured ? 'var(--accent)' : 'var(--text-secondary)' }}>
                {apiConfig.ai_configured ? 'Gemini Live' : 'Fallback Local'}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <main className="main-content">
        <header className="dashboard-header">
          <div className="header-title-section">
            <h1>Vijayawada City Dashboard</h1>
          </div>
          <div className="header-actions">
            {activeScenario && (
              <div className="alert-body" style={{ marginRight: '16px', background: 'rgba(245,158,11,0.06)', padding: '6px 16px', borderRadius: '8px', border: '1px solid rgba(245,158,11,0.2)' }}>
                <AlertTriangle size={16} color="var(--warning)" style={{ marginRight: '8px' }} />
                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--warning)' }}>Simulation Active</span>
              </div>
            )}
            <button className="btn-reset" onClick={handleReset}>
              <RefreshCw size={14} />
              <span>Reset Twin Network</span>
            </button>
          </div>
        </header>

        {/* Dashboard Grid Viewports */}
        <div className="dashboard-viewport">
          
          {/* Quick Metrics Bar */}
          <div className="metrics-grid">
            <div className={`metric-card neutral`}>
              <div className="metric-header">
                <span className="metric-title">Avg Travel Time</span>
                <Clock className="metric-icon" size={18} />
              </div>
              <div className="metric-value">{displayMetrics.average_travel_time_minutes}m</div>
              <div className="metric-sub">Mean path routing travel delay</div>
            </div>
            
            <div className={`metric-card ${displayMetrics.network_efficiency > 80 ? 'success' : displayMetrics.network_efficiency > 50 ? 'warning' : 'danger'}`}>
              <div className="metric-header">
                <span className="metric-title">Network Efficiency</span>
                <Activity className="metric-icon" size={18} />
              </div>
              <div className="metric-value">{displayMetrics.network_efficiency}%</div>
              <div className="metric-sub">Network health against baseline</div>
            </div>

            <div className={`metric-card ${displayMetrics.congested_roads_count > 0 ? 'danger' : 'success'}`}>
              <div className="metric-header">
                <span className="metric-title">Congested Segments</span>
                <TrendingUp className="metric-icon" size={18} />
              </div>
              <div className="metric-value">{displayMetrics.congested_roads_count}</div>
              <div className="metric-sub">Road links above 80% capacity</div>
            </div>

            <div className={`metric-card ${displayMetrics.failed_commutes_count > 0 ? 'danger' : 'success'}`}>
              <div className="metric-header">
                <span className="metric-title">Blocked Commuters</span>
                <Users className="metric-icon" size={18} />
              </div>
              <div className="metric-value">{displayMetrics.failed_commutes_count}</div>
              <div className="metric-sub">Commuters stranded (no paths)</div>
            </div>
          </div>

          {/* TAB 1: Digital Twin Map View */}
          {activeTab === 'digital-twin' && (
            <div className="content-layout-grid">
              
              {/* Map Panel */}
              <div className="map-card">
                <div className="card-header">
                  <h2>
                    <MapIcon size={18} color="var(--accent)" />
                    <span>Real-Time Traffic Network Grid</span>
                  </h2>
                  <div className="map-legend">
                    <div className="legend-item">
                      <span className="legend-color" style={{ backgroundColor: '#10b981' }} />
                      <span>Clear</span>
                    </div>
                    <div className="legend-item">
                      <span className="legend-color" style={{ backgroundColor: '#f59e0b' }} />
                      <span>Moderate</span>
                    </div>
                    <div className="legend-item">
                      <span className="legend-color" style={{ backgroundColor: '#f43f5e' }} />
                      <span>Heavy</span>
                    </div>
                    <div className="legend-item">
                      <span className="legend-color" style={{ backgroundColor: '#64748b' }} />
                      <span>Closed</span>
                    </div>
                  </div>
                </div>

                <div className="map-container-inner" style={{ height: '530px' }}>
                  {cityData && (
                    <RoadNetworkMap
                      roads={cityData.roads}
                      intersections={cityData.intersections}
                      facilities={cityData.facilities}
                      populationZones={cityData.population_zones}
                      
                      selectedRoad={selectedRoad}
                      selectedIntersection={selectedIntersection}
                      selectedFacility={selectedFacility}
                      selectedZone={selectedZone}
                      
                      onSelectRoad={(road) => {
                        setSelectedRoad(road);
                        setSelectedIntersection(null);
                        setSelectedFacility(null);
                        setSelectedZone(null);
                      }}
                      onSelectIntersection={(node) => {
                        setSelectedIntersection(node);
                        setSelectedRoad(null);
                        setSelectedFacility(null);
                        setSelectedZone(null);
                      }}
                      onSelectFacility={(fac) => {
                        setSelectedFacility(fac);
                        setSelectedRoad(null);
                        setSelectedIntersection(null);
                        setSelectedZone(null);
                      }}
                      onSelectZone={(zone) => {
                        setSelectedZone(zone);
                        setSelectedRoad(null);
                        setSelectedIntersection(null);
                        setSelectedFacility(null);
                      }}
                      thresholds={apiConfig.congestion_thresholds || { clear: 0.3, moderate: 0.7 }}
                    />
                  )}
                </div>
              </div>

              {/* Side Panels (Details Cards) */}
              <div className="side-panel">
                
                {/* 1. Interactive Details Card */}
                {selectedRoad ? (
                  <div className="panel-card">
                    <h3>
                      <Shield size={16} color="var(--accent)" />
                      <span>Road Segment Details</span>
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div className="detail-item">
                        <span className="detail-label">Name</span>
                        <span className="detail-value">{selectedRoad.name}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">ID</span>
                        <span className="detail-value">{selectedRoad.id}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Status</span>
                        <span className={`detail-badge ${selectedRoad.availability === 1 ? 'badge-clear' : 'badge-closed'}`}>
                          {selectedRoad.availability === 1 ? 'AVAILABLE' : 'BLOCKED'}
                        </span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Congestion Index</span>
                        <span className={`detail-value ${
                          selectedRoad.current_volume / selectedRoad.capacity > 0.95 ? 'congested' :
                          selectedRoad.current_volume / selectedRoad.capacity > 0.5 ? 'moderate' : 'clear'
                        }`}>
                          {getCongestionLabel(selectedRoad.current_volume / selectedRoad.capacity, selectedRoad.availability)}
                        </span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Current Volume</span>
                        <span className="detail-value">{selectedRoad.current_volume} vehicles</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Safety Capacity</span>
                        <span className="detail-value">{selectedRoad.capacity} vehicles</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Speed Limit</span>
                        <span className="detail-value">{selectedRoad.speed_limit_kmh} km/h</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Criticality Multiplier</span>
                        <span className="detail-value">{selectedRoad.criticality}x</span>
                      </div>
                      
                      <button 
                        className={`btn-block-action ${selectedRoad.availability === 1 ? 'block' : 'unblock'}`}
                        onClick={() => handleToggleRoadAvailability(selectedRoad.id, selectedRoad.availability)}
                        disabled={simulationLoading}
                      >
                        {simulationLoading ? 'Updating...' : selectedRoad.availability === 1 ? 'Simulate Blockage' : 'Open Segment'}
                      </button>
                    </div>
                  </div>
                ) : selectedIntersection ? (
                  <div className="panel-card">
                    <h3>
                      <MapPin size={16} color="var(--accent)" />
                      <span>Intersection Junction Details</span>
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div className="detail-item">
                        <span className="detail-label">Name</span>
                        <span className="detail-value">{selectedIntersection.name}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Node ID</span>
                        <span className="detail-value">{selectedIntersection.id}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Latitude</span>
                        <span className="detail-value">{selectedIntersection.latitude}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Longitude</span>
                        <span className="detail-value">{selectedIntersection.longitude}</span>
                      </div>
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', lineHeight: '1.4' }}>
                        This intersection acts as a major link point in the Vijayawada transport grid. Click connected links on the map to evaluate flow vectors.
                      </p>
                    </div>
                  </div>
                ) : selectedFacility ? (
                  <div className="panel-card">
                    <h3>
                      <MapPin size={16} color="var(--danger)" />
                      <span>Emergency Facility</span>
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div className="detail-item">
                        <span className="detail-label">Facility</span>
                        <span className="detail-value">{selectedFacility.name}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Type</span>
                        <span className="detail-value">{selectedFacility.type}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Nearest Junction</span>
                        <span className="detail-value">{selectedFacility.nearest_node}</span>
                      </div>
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', lineHeight: '1.4' }}>
                        Traffic blocks surrounding this facility's nearest junction will delay emergency response routes. Monitor congestion indices on surrounding arterial lines.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="panel-card">
                    <h3>
                      <Eye size={16} color="var(--text-secondary)" />
                      <span>Map Inspector</span>
                    </h3>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                      Click on any intersection node, facility, or road link segment directly on the map to inspect live metrics, simulate blocks, and adjust volumes.
                    </p>
                  </div>
                )}

                {/* 2. Run Optimization Quick CTA */}
                {activeScenario && !optimizationData && (
                  <div className="panel-card" style={{ background: 'linear-gradient(135deg, var(--bg-secondary) 0%, rgba(16,185,129,0.05) 100%)', border: '1px solid rgba(16,185,129,0.25)' }}>
                    <h3 style={{ border: 'none', padding: '0', margin: '0 0 12px 0' }}>
                      <Cpu size={16} color="var(--success)" />
                      <span>AI Re-routing Available</span>
                    </h3>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: '1.5' }}>
                      Active traffic simulation has detected bottlenecks. Run the AI traffic optimizer to simulate alternative route plans and generate deployment solutions.
                    </p>
                    <button 
                      className="btn-optimize-run" 
                      onClick={handleRunOptimization}
                      disabled={optimizationLoading}
                    >
                      {optimizationLoading ? 'Generating Plans...' : 'Execute AI Traffic Optimization'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: Scenario Simulator Control Panel */}
          {activeTab === 'simulator' && (
            <div className="content-layout-grid">
              
              {/* Form card */}
              <div className="panel-card">
                <h3>
                  <Play size={16} color="var(--accent)" />
                  <span>Launch Custom Traffic Scenario</span>
                </h3>
                <form className="simulator-form" onSubmit={handleLaunchScenario}>
                  
                  <div className="form-group">
                    <label>Disruption Scenario Type</label>
                    <select value={formType} onChange={e => { setFormType(e.target.value); setFormTarget(''); }}>
                      <option value="ROAD_CLOSURE">Road Segment Closure</option>
                      <option value="ACCIDENT">Intersection / Road Accident</option>
                      <option value="TRAFFIC_SURGE">High Volume Commute Surge</option>
                      <option value="WEATHER_EVENT">Severe Weather Condition (Rain/Storm)</option>
                    </select>
                  </div>

                  {formType !== 'WEATHER_EVENT' && (
                    <div className="form-group">
                      <label>Target Entity</label>
                      <select value={formTarget} onChange={e => setFormTarget(e.target.value)}>
                        <option value="">-- Choose Segment / Intersection --</option>
                        {formType === 'ROAD_CLOSURE' && cityData?.roads.map(r => (
                          <option key={r.id} value={r.id}>{r.name} ({r.road_type})</option>
                        ))}
                        {formType === 'ACCIDENT' && (
                          <>
                            <optgroup label="Intersections (Nodes)">
                              {cityData?.intersections.map(i => (
                                <option key={i.id} value={i.id}>{i.name}</option>
                              ))}
                            </optgroup>
                            <optgroup label="Roads (Edges)">
                              {cityData?.roads.map(r => (
                                <option key={r.id} value={r.id}>{r.name}</option>
                              ))}
                            </optgroup>
                          </>
                        )}
                        {formType === 'TRAFFIC_SURGE' && cityData?.population_zones.map(z => (
                          <option key={z.id} value={z.nearest_node}>Surge Originating near {z.name}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {formType === 'TRAFFIC_SURGE' && (
                    <div className="form-group">
                      <label>Surge Volume Multiplier: {formSurgeFactor}x</label>
                      <input 
                        type="range" 
                        min="1.2" 
                        max="3.0" 
                        step="0.1" 
                        value={formSurgeFactor} 
                        onChange={e => setFormSurgeFactor(parseFloat(e.target.value))} 
                      />
                    </div>
                  )}

                  {formType === 'WEATHER_EVENT' && (
                    <div className="form-group">
                      <label>Network Speed Reduction: {Math.round(formSpeedReduction * 100)}%</label>
                      <input 
                        type="range" 
                        min="0.1" 
                        max="0.6" 
                        step="0.05" 
                        value={formSpeedReduction} 
                        onChange={e => setFormSpeedReduction(parseFloat(e.target.value))} 
                      />
                    </div>
                  )}

                  <button className="btn-submit" type="submit" disabled={simulationLoading}>
                    {simulationLoading ? 'Calculating Grid Flows...' : 'Simulate & Calculate Impact'}
                  </button>
                </form>
              </div>

              {/* History list card */}
              <div className="panel-card">
                <h3>
                  <Calendar size={16} color="var(--text-secondary)" />
                  <span>Simulation History</span>
                </h3>
                <div className="history-list">
                  {scenariosHistory.length === 0 ? (
                    <p style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', marginTop: '20px' }}>
                      No scenarios simulated yet. Use the launch form to create one.
                    </p>
                  ) : (
                    scenariosHistory.map((item, index) => (
                      <div key={item.id || index} className="history-item">
                        <div className="history-item-info">
                          <span className="history-item-title">{item.type.replace('_', ' ')}</span>
                          <span className="history-item-time">{new Date(item.created_at).toLocaleTimeString()}</span>
                        </div>
                        <span className="detail-badge badge-clear">{item.status}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

            </div>
          )}

          {/* TAB 3: AI Traffic Optimizer View */}
          {activeTab === 'optimizer' && optimizationData && (
            <div className="optimizer-layout">
              
              {/* Cards for candidate plans */}
              <div className="plans-row">
                {optimizationData.candidate_plans.map(plan => {
                  const isRec = plan.plan_id === optimizationData.recommended_plan_id;
                  return (
                    <div key={plan.plan_id} className={`plan-card ${isRec ? 'recommended' : ''}`}>
                      {isRec && <div className="recommended-badge">AI Recommendation</div>}
                      <span className="plan-name">{plan.name}</span>
                      <p className="plan-desc">{plan.description}</p>
                      
                      <div className="plan-metrics">
                        <div>
                          <div className="plan-metric-val">{plan.metrics.average_travel_time_minutes}m</div>
                          <div className="plan-metric-lbl">Travel Time</div>
                        </div>
                        <div>
                          <div className="plan-metric-val">{plan.metrics.network_efficiency}%</div>
                          <div className="plan-metric-lbl">Efficiency</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Narrative Report */}
              <div className="report-card">
                <div className="report-header">
                  <Cpu size={22} color="var(--accent)" />
                  <h3>AI Mobility Optimization Report</h3>
                </div>
                <div className="report-markdown">
                  <div dangerouslySetInnerHTML={{ __html: optimizationData.narrative
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/### (.*?)\n/g, '<h3>$1</h3>')
                    .replace(/\* (.*?)\n/g, '<li>$1</li>')
                    .replace(/\n\n/g, '<p></p>')
                  }} />
                </div>
              </div>

            </div>
          )}

        </div>
      </main>
    </div>
  );
}

export default App;
