import { useState, useEffect } from 'react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, BarChart, Bar 
} from 'recharts';
import { 
  LayoutDashboard, Activity, Database, Server, Lock, 
  Thermometer, ShieldAlert, Zap, RefreshCw, Trash2, Smartphone
} from 'lucide-react';
import CountUp from 'react-countup';
import './App.css';

function App() {
  const [data, setData] = useState([]);
  const [status, setStatus] = useState("Connecting...");
  const [activeTab, setActiveTab] = useState('dashboard');

  // --- FETCH DATA ---
  const fetchData = () => {
    fetch('http://localhost:5000/api/blockchain')
      .then(res => res.json())
      .then(blockchain => {
        if (!Array.isArray(blockchain)) return;
        const validData = blockchain
          .filter(block => block.data && block.data.temperature)
          .map(block => ({
            ...block.data,
            id: block.index,
            hash: block.previous_hash,
            timeDisplay: block.timestamp ? block.timestamp.split(' ')[1].split('.')[0] : ''
          }));
        setData(validData);
        setStatus("System Online");
      })
      .catch(() => setStatus("Offline"));
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, []);

  // --- STATS LOGIC ---
  const latest = data.length > 0 ? data[data.length - 1] : null;
  const threatCount = data.filter(d => d.trust_status && d.trust_status.includes("Malicious")).length;
  const isAttack = latest && latest.temperature > 80;
  const trustScore = latest ? Math.round(latest.confidence * 100) : 0;
  
  const pieData = [
    { name: 'Trust', value: trustScore },
    { name: 'Risk', value: 100 - trustScore }
  ];

  // --- VIEW RENDERER ---
  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <>
            {/* 1. TOP STATS ROW (Back to 4 Cards) */}
            <div className="stats-row">
              {/* Card 1: Temp */}
              <div className="card">
                <div className="card-icon-bg" style={{background: 'rgba(0, 243, 255, 0.1)', color: '#00f3ff'}}>
                  <Thermometer size={24} />
                </div>
                <div className="stat-value" style={{color: isAttack ? '#ff0055' : 'white'}}>
                  {latest ? <CountUp end={latest.temperature} decimals={1} suffix="°C" duration={0.5}/> : '--'}
                </div>
                <div className="stat-label">Live Temperature</div>
              </div>

              {/* Card 2: Blocks */}
              <div className="card">
                 <div className="card-icon-bg" style={{background: 'rgba(188, 19, 254, 0.1)', color: '#bc13fe'}}>
                  <Database size={24} />
                </div>
                <div className="stat-value"><CountUp end={data.length} duration={0.5} prefix="#"/></div>
                <div className="stat-label">Total Blocks Mined</div>
              </div>

              {/* Card 3: Threats */}
              <div className="card">
                 <div className="card-icon-bg" style={{background: 'rgba(255, 0, 85, 0.1)', color: '#ff0055'}}>
                  <ShieldAlert size={24} />
                </div>
                <div className="stat-value" style={{color: threatCount > 0 ? '#ff0055' : 'white'}}>
                  <CountUp end={threatCount} duration={0.5}/>
                </div>
                <div className="stat-label">Threats Blocked</div>
              </div>

              {/* Card 4: Uptime */}
              <div className="card">
                 <div className="card-icon-bg" style={{background: 'rgba(0, 255, 153, 0.1)', color: '#00ff99'}}>
                  <Zap size={24} />
                </div>
                <div className="stat-value">99.9%</div>
                <div className="stat-label">System Uptime</div>
              </div>
            </div>

            {/* 2. MAIN CHARTS ROW */}
            <div className="charts-row">
              <div className="card chart-card">
                <h3 style={{marginTop:0, marginBottom: 20}}>Live Temperature Trend</h3>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data}>
                    <defs>
                      <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00f3ff" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#00f3ff" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                    <XAxis dataKey="timeDisplay" stroke="#666" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#666" fontSize={12} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                    <Tooltip contentStyle={{backgroundColor: '#111', border: '1px solid #333', borderRadius: '10px'}} itemStyle={{color: '#00f3ff'}} />
                    <Area type="monotone" dataKey="temperature" stroke="#00f3ff" strokeWidth={3} fill="url(#colorTemp)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="card circle-card" style={{alignItems: 'center', justifyContent: 'center'}}>
                <h3 style={{margin: '0 0 20px 0', width:'100%', textAlign:'left'}}>Trust Score</h3>
                <div style={{height: 200, width: '100%', display:'flex', justifyContent:'center', alignItems:'center', position:'relative'}}>
                  <PieChart width={180} height={180}>
                    <Pie data={pieData} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value" stroke="none">
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === 0 ? (trustScore > 50 ? '#00ff99' : '#ff0055') : '#222'} />
                      ))}
                    </Pie>
                  </PieChart>
                  <div style={{position: 'absolute', textAlign: 'center'}}>
                     <div style={{fontSize: '2rem', fontWeight: 'bold', color: trustScore > 50 ? '#00ff99' : '#ff0055'}}>
                       {trustScore}%
                     </div>
                  </div>
                </div>
                <p style={{color: '#666', fontSize: '0.9rem', marginTop: 10}}>AI Model Confidence</p>
              </div>
            </div>

            {/* 3. RECENT LOGS */}
            <div className="logs-card">
              <h3 style={{margin:0}}>Recent Activity</h3>
              <table className="log-table">
                <thead><tr><th>STATUS</th><th>HASH</th><th>TIME</th><th>TEMP</th></tr></thead>
                <tbody>
                  {[...data].reverse().slice(0, 5).map((item, index) => (
                    <tr key={index}>
                      <td><span className={`badge ${item.trust_status.includes("Trusted") ? 'badge-trusted' : 'badge-malicious'}`}>{item.trust_status.toUpperCase()}</span></td>
                      <td style={{color: '#666'}}>{item.hash ? item.hash.substring(0, 16) : 'GENESIS'}...</td>
                      <td style={{color: '#fff'}}>{item.timeDisplay}</td>
                      <td>{item.temperature}°C</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        );

      case 'analytics':
        return (
          <div style={{display:'flex', flexDirection:'column', gap:'20px'}}>
             <div className="card" style={{height: '350px'}}>
                <h3>Humidity Analysis</h3>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false}/>
                    <XAxis dataKey="timeDisplay" stroke="#666"/>
                    <YAxis stroke="#666"/>
                    <Tooltip cursor={{fill: 'rgba(255,255,255,0.05)'}} contentStyle={{backgroundColor: '#111', border: '1px solid #333'}} />
                    <Bar dataKey="humidity" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
             </div>
             <div className="card" style={{height: '350px'}}>
                <h3>Trust Fluctuation</h3>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data}>
                    <defs>
                      <linearGradient id="colorConf" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00ff99" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#00ff99" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false}/>
                    <XAxis dataKey="timeDisplay" stroke="#666"/>
                    <YAxis stroke="#666"/>
                    <Tooltip contentStyle={{backgroundColor: '#111', border: '1px solid #333'}} />
                    <Area type="step" dataKey="confidence" stroke="#00ff99" strokeWidth={2} fill="url(#colorConf)" />
                  </AreaChart>
                </ResponsiveContainer>
             </div>
          </div>
        );

      case 'blockchain':
        return (
          <div className="logs-card" style={{height: '100%', overflow: 'hidden', display:'flex', flexDirection:'column'}}>
            <div style={{display:'flex', justifyContent:'space-between', marginBottom:20}}>
              <h3>Full Blockchain Ledger</h3>
              <div style={{color:'#666'}}>{data.length} Blocks Verified</div>
            </div>
            <div style={{overflowY:'auto', flex:1}}>
              <table className="log-table">
                <thead style={{position:'sticky', top:0, background:'#0f0f0f'}}>
                  <tr><th>ID</th><th>STATUS</th><th>FULL HASH</th><th>TIMESTAMP</th><th>DATA</th></tr>
                </thead>
                <tbody>
                  {[...data].reverse().map((item, index) => (
                    <tr key={index}>
                      <td style={{color:'#888'}}>#{item.id}</td>
                      <td><span className={`badge ${item.trust_status.includes("Trusted") ? 'badge-trusted' : 'badge-malicious'}`}>{item.trust_status}</span></td>
                      <td style={{fontFamily:'monospace', fontSize:'0.8rem', color:'#666'}}>{item.hash}</td>
                      <td>{item.timeDisplay}</td>
                      <td>T: {item.temperature}°C | H: {item.humidity}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      
      case 'nodes':
        return (
          <div className="stats-row">
            <div className="card" style={{textAlign:'center', alignItems:'center', justifyContent:'center', minHeight:'300px'}}>
              <Smartphone size={64} color="#00f3ff" style={{marginBottom:20}} />
              <h2>Mobile Sensor Node</h2>
              <p style={{color:'#888'}}>ID: XJ-920-MOBILE</p>
              <div className="badge badge-trusted" style={{marginTop:10}}>ONLINE</div>
              <p style={{marginTop:20}}>IP: 192.168.1.6</p>
            </div>
             <div className="card" style={{textAlign:'center', alignItems:'center', justifyContent:'center', minHeight:'300px'}}>
              <Server size={64} color="#8b5cf6" style={{marginBottom:20}} />
              <h2>Python Backend</h2>
              <p style={{color:'#888'}}>ID: LOCALHOST-5000</p>
              <div className="badge badge-trusted" style={{marginTop:10}}>ACTIVE</div>
              <p style={{marginTop:20}}>Latency: 12ms</p>
            </div>
          </div>
        );

      case 'admin':
        return (
          <div className="card" style={{maxWidth: '600px', margin:'0 auto'}}>
             <h3>System Administration</h3>
             <div style={{marginTop: 30}}>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', padding:'20px 0', borderBottom:'1px solid #333'}}>
                  <div>
                    <h4>Flush Database</h4>
                    <p style={{color:'#666', fontSize:'0.9rem', margin:0}}>Delete all blockchain records (Irreversible)</p>
                  </div>
                  <button style={{background:'#ff0055', color:'white', border:'none', padding:'10px 20px', borderRadius:'8px', cursor:'pointer', display:'flex', gap:10}}>
                    <Trash2 size={18}/> Clear DB
                  </button>
                </div>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', padding:'20px 0'}}>
                  <div>
                    <h4>Restart Inference Engine</h4>
                    <p style={{color:'#666', fontSize:'0.9rem', margin:0}}>Reload the Isolation Forest Model</p>
                  </div>
                  <button style={{background:'#00f3ff', color:'black', border:'none', padding:'10px 20px', borderRadius:'8px', cursor:'pointer', display:'flex', gap:10}}>
                    <RefreshCw size={18}/> Restart
                  </button>
                </div>
             </div>
          </div>
        );

      default:
        return <div>Select a tab</div>;
    }
  };

  return (
    <div className="app-container">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="brand">
          <div style={{background: '#00f3ff', width: 10, height: 10, borderRadius: '50%'}}></div>
          TrustChain
        </div>
        <nav className="nav-links">
          <div className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <LayoutDashboard size={20} /> Dashboard
          </div>
          <div className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
            <Activity size={20} /> Analytics
          </div>
          <div className={`nav-item ${activeTab === 'blockchain' ? 'active' : ''}`} onClick={() => setActiveTab('blockchain')}>
            <Database size={20} /> Blockchain
          </div>
          <div className={`nav-item ${activeTab === 'nodes' ? 'active' : ''}`} onClick={() => setActiveTab('nodes')}>
            <Server size={20} /> Nodes
          </div>
          <div className={`nav-item ${activeTab === 'admin' ? 'active' : ''}`} onClick={() => setActiveTab('admin')} style={{marginTop: 'auto'}}>
            <Lock size={20} /> Admin
          </div>
        </nav>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="main-content">
        <header className="header">
          <div className="page-title">
            <h1 style={{textTransform:'capitalize'}}>{activeTab}</h1>
            <p>Real-time IoT Security Telemetry</p>
          </div>
          <div className={`status-badge ${status === "System Online" ? 'online' : 'offline'}`}>
            {status}
          </div>
        </header>

        {/* DYNAMIC CONTENT AREA */}
        <div style={{flex: 1, minHeight: 0}}>
          {renderContent()}
        </div>
      </main>
    </div>
  );
}

export default App;