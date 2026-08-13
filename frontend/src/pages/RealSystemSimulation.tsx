import { useEffect, useCallback } from 'react'
import { useSimulationStore } from '../store/useSimulationStore'
import { requestMicPermission, novaSilence } from '../engine/novaSpeech'
import { startLiveTelemetryStream, stopLiveTelemetryStream, startRealVoiceListener, stopRealVoiceListener } from '../engine/realSystemEngine'
import PlantTwin from '../components/demo/PlantTwin'
import NovaPresenceIndicator from '../components/demo/NovaPresenceIndicator'
import EvidencePanel from '../components/demo/EvidencePanel'
import AuthorizationOverlay from '../components/demo/AuthorizationOverlay'
import EventLog from '../components/demo/EventLog'
import DemoOverlays from '../components/demo/DemoOverlays'

export default function RealSystemSimulation() {
  const {
    isRunning,
    startSimulation,
    stopSimulation,
    activeOverlayView,
    setOverlayView,
    evidenceOpen,
    setEvidenceOpen,
    triggerAnomaly,
    resetTelemetry,
    focusedZone,
    sensors,
    compoundRiskScore,
  } = useSimulationStore()

  const handleStart = useCallback(async () => {
    await requestMicPermission()
    startSimulation()
    startLiveTelemetryStream()
    startRealVoiceListener()
  }, [startSimulation])

  const handleStop = useCallback(() => {
    stopLiveTelemetryStream()
    stopRealVoiceListener()
    novaSilence()
    stopSimulation()
  }, [stopSimulation])

  useEffect(() => {
    handleStart()
    return () => {
      stopLiveTelemetryStream()
      stopRealVoiceListener()
      novaSilence()
    }
  }, [handleStart])

  if (!isRunning) {
    return <SimulationLanding onStart={handleStart} />
  }

  const h2s = sensors.find(s => s.type === 'H₂S' && s.zone === (focusedZone || 'Bay 3'))
  const press = sensors.find(s => s.type === 'Pressure' && s.zone === (focusedZone || 'Bay 3'))
  const temp = sensors.find(s => s.type === 'Temp' && s.zone === (focusedZone || 'Bay 3'))

  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: '#F7F6F2',
      position: 'relative',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Background Grid */}
      <div style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: 'linear-gradient(rgba(200,201,198,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(200,201,198,0.18) 1px, transparent 1px)',
        backgroundSize: '60px 60px',
        pointerEvents: 'none',
      }} />

      {/* ─── Top Navigation Bar ────────────────────────────────────────────── */}
      <div style={{
        height: '52px',
        background: '#FFFFFF',
        borderBottom: '1px solid #E9E9E5',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        zIndex: 50,
        boxShadow: '0 1px 4px rgba(0,0,0,0.03)',
      }}>
        {/* Brand & Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <NovaLogoSmall />
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.55rem',
            color: '#D98A3A',
            background: '#F3DFC0',
            border: '1px solid #D98A3A',
            padding: '3px 8px',
            borderRadius: '12px',
            letterSpacing: '0.08em',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#D98A3A' }} />
            LIVE AGENT SIMULATION (NON-SCRIPTED)
          </div>
        </div>

        {/* Center Navigation Pills */}
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {[
            { id: 'none', label: 'Plant View' },
            { id: 'tracks', label: 'Recent Tracks' },
            { id: 'audit', label: 'Audit Trail' },
            { id: 'signals', label: 'Signals' },
          ].map(view => (
            <button
              key={view.id}
              onClick={() => setOverlayView(view.id as any)}
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: '0.72rem',
                fontWeight: 600,
                color: activeOverlayView === view.id ? '#0E0D1F' : '#62636A',
                background: 'transparent',
                border: 'none',
                borderBottom: activeOverlayView === view.id ? '2px solid #D9534F' : '2px solid transparent',
                padding: '12px 14px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              {view.label}
            </button>
          ))}
          <button
            onClick={() => setEvidenceOpen(!evidenceOpen)}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '0.72rem',
              fontWeight: 600,
              color: evidenceOpen ? '#D9534F' : '#62636A',
              background: 'transparent',
              border: 'none',
              borderBottom: evidenceOpen ? '2px solid #D9534F' : '2px solid transparent',
              padding: '12px 14px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            Evidence Drawer
          </button>
        </div>

        {/* Anomaly Controls & Exit */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={() => triggerAnomaly('Bay 3', 'gas')}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '0.7rem',
              fontWeight: 600,
              color: '#2C2D30',
              background: '#FFFFFF',
              border: '1px solid #E9E9E5',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
            }}
          >
            Inject Gas Leak
          </button>
          <button
            onClick={() => triggerAnomaly('Bay 2', 'pressure')}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '0.7rem',
              fontWeight: 600,
              color: '#2C2D30',
              background: '#FFFFFF',
              border: '1px solid #E9E9E5',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
            }}
          >
            Inject Pressure Spike
          </button>
          <button
            onClick={resetTelemetry}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '0.7rem',
              fontWeight: 600,
              color: '#62636A',
              background: '#FFFFFF',
              border: '1px solid #E9E9E5',
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
            }}
          >
            <span>↺</span> Reset Telemetry
          </button>
          <button
            onClick={handleStop}
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '0.7rem',
              fontWeight: 700,
              color: '#FFFFFF',
              background: '#D9534F',
              border: 'none',
              padding: '7px 18px',
              borderRadius: '6px',
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(217,83,79,0.3)',
              letterSpacing: '0.04em',
            }}
          >
            EXIT SIMULATION
          </button>
        </div>
      </div>

      {/* ─── Main Workspace (Icon Rail + Audit Log + Center View) ────────────── */}
      <div style={{
        flex: 1,
        display: 'flex',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Leftmost 60px Icon Navigation Rail */}
        <div style={{
          width: '56px',
          height: '100%',
          background: '#FFFFFF',
          borderRight: '1px solid #E9E9E5',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '16px 0',
          justifyContent: 'space-between',
          zIndex: 25,
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '22px', alignItems: 'center' }}>
            {/* 1. Plant View */}
            <button
              onClick={() => { setOverlayView('none'); setEvidenceOpen(false) }}
              style={{ background: 'none', border: 'none', color: activeOverlayView === 'none' && !evidenceOpen ? '#D9534F' : '#A0A2A8', cursor: 'pointer', transition: 'color 0.2s ease' }}
              title="Plant View"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 21h18M3 7v14M21 7v14M6 21V11m4 10V11m4 10V11m4 10V11M9 7l3-4 3 4"/></svg>
            </button>

            {/* 2. Recent Tracks */}
            <button
              onClick={() => { setOverlayView('tracks'); setEvidenceOpen(false) }}
              style={{ background: 'none', border: 'none', color: activeOverlayView === 'tracks' ? '#D9534F' : '#A0A2A8', cursor: 'pointer', transition: 'color 0.2s ease' }}
              title="Recent Tracks"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            </button>

            {/* 3. Audit Trail */}
            <button
              onClick={() => { setOverlayView('audit'); setEvidenceOpen(false) }}
              style={{ background: 'none', border: 'none', color: activeOverlayView === 'audit' ? '#D9534F' : '#A0A2A8', cursor: 'pointer', transition: 'color 0.2s ease' }}
              title="Audit Trail"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
            </button>

            {/* 4. Signals */}
            <button
              onClick={() => { setOverlayView('signals'); setEvidenceOpen(false) }}
              style={{ background: 'none', border: 'none', color: activeOverlayView === 'signals' ? '#D9534F' : '#A0A2A8', cursor: 'pointer', transition: 'color 0.2s ease' }}
              title="Signals"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
            </button>

            {/* 5. Evidence Drawer */}
            <button
              onClick={() => setEvidenceOpen(!evidenceOpen)}
              style={{ background: 'none', border: 'none', color: evidenceOpen ? '#D9534F' : '#A0A2A8', cursor: 'pointer', transition: 'color 0.2s ease' }}
              title="Evidence Drawer"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            </button>
          </div>

          <div style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: '#F3DFC0',
            color: '#D98A3A',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.65rem',
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid #D98A3A',
          }}>
            PH
          </div>
        </div>

        {/* Real-time Audit Log Column (240px wide) */}
        <div style={{
          width: '240px',
          height: '100%',
          borderRight: '1px solid #E9E9E5',
          background: '#FFFFFF',
          zIndex: 20,
        }}>
          <EventLog />
        </div>

        {/* Central Canvas & Bottom Dashboard Grid */}
        <div style={{
          flex: 1,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          background: '#F7F6F2',
          marginRight: evidenceOpen ? '380px' : '0',
          transition: 'margin-right 0.4s ease',
        }}>
          {/* Zone Header Bar */}
          <div style={{
            padding: '12px 20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'transparent',
            zIndex: 10,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#D9534F' }} />
              <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.85rem', fontWeight: 800, color: '#2C2D30', letterSpacing: '0.04em' }}>
                {focusedZone ? focusedZone.toUpperCase() : 'BAY 3 - COMPRESSOR C-14 ZONE'}
              </span>
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '0.55rem',
                fontWeight: 800,
                color: '#D9534F',
                background: '#FFF3EE',
                border: '1px solid #FCDAD7',
                padding: '2px 8px',
                borderRadius: '4px',
                letterSpacing: '0.05em',
              }}>
                ⚠ CRITICAL ALERT
              </span>
            </div>

            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.6rem',
              color: '#2C2D30',
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#72856C' }} />
              LIVE
            </div>
          </div>

          {/* Plant Twin Canvas Area (62% height) */}
          <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
            <PlantTwin />
          </div>

          {/* Bottom 4-Card Dashboard Grid (190px height) */}
          <div style={{
            height: '190px',
            padding: '12px 20px 16px 20px',
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '14px',
            zIndex: 15,
          }}>
            {/* Card 1: Plant Overview */}
            <div style={{
              background: '#FFFFFF',
              border: '1px solid #E9E9E5',
              borderRadius: '8px',
              padding: '14px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}>
              <div>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.55rem', color: '#8E9096', letterSpacing: '0.08em', fontWeight: 800 }}>
                  PLANT OVERVIEW
                </div>
                <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.68rem', color: '#62636A', marginTop: '2px' }}>
                  Live status at a glance
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <div>
                  <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '1.4rem', fontWeight: 800, color: '#2C2D30', lineHeight: 1 }}>12</div>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.5rem', color: '#8E9096', marginTop: '4px' }}>Total Bays</div>
                </div>
                <div>
                  <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '1.4rem', fontWeight: 800, color: '#D98A3A', lineHeight: 1 }}>3</div>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.5rem', color: '#8E9096', marginTop: '4px' }}>Active Alerts</div>
                </div>
                <div>
                  <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '1.4rem', fontWeight: 800, color: '#72856C', lineHeight: 1 }}>98.6%</div>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.5rem', color: '#8E9096', marginTop: '4px' }}>System Health</div>
                </div>
              </div>
            </div>

            {/* Card 2: Risk Trend (Bay 3) */}
            <div style={{
              background: '#FFFFFF',
              border: '1px solid #E9E9E5',
              borderRadius: '8px',
              padding: '14px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.55rem', color: '#8E9096', letterSpacing: '0.08em', fontWeight: 800 }}>
                  RISK TREND (BAY 3)
                </div>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.55rem', color: '#D98A3A', fontWeight: 800 }}>↑ 24%</span>
              </div>
              {/* Sparkline curve */}
              <div style={{ height: '45px', width: '100%', margin: '4px 0' }}>
                <svg width="100%" height="100%" viewBox="0 0 200 45" preserveAspectRatio="none">
                  <path d="M 0 35 Q 30 30, 60 25 T 120 18 T 180 8 L 200 6" fill="none" stroke="#D98A3A" strokeWidth="2" />
                  <path d="M 0 35 Q 30 30, 60 25 T 120 18 T 180 8 L 200 6 V 45 H 0 Z" fill="rgba(217,138,58,0.1)" />
                </svg>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: "'JetBrains Mono', monospace", fontSize: '0.5rem', color: '#A0A2A8' }}>
                <span>10:30</span><span>11:00</span><span>11:30</span><span>12:00</span><span>12:30</span><span>13:00</span>
              </div>
            </div>

            {/* Card 3: Active Permits */}
            <div style={{
              background: '#FFFFFF',
              border: '1px solid #E9E9E5',
              borderRadius: '8px',
              padding: '14px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.55rem', color: '#8E9096', letterSpacing: '0.08em', fontWeight: 800 }}>
                ACTIVE PERMITS
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', margin: '4px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.62rem', fontFamily: "'Inter', sans-serif" }}>
                  <span style={{ color: '#D9534F', fontWeight: 700 }}>● PTW-0441</span>
                  <span style={{ color: '#62636A' }}>Hot-Work - Bay 3</span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#A0A2A8', fontSize: '0.55rem' }}>16:00</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.62rem', fontFamily: "'Inter', sans-serif" }}>
                  <span style={{ color: '#72856C', fontWeight: 700 }}>● PTW-0433</span>
                  <span style={{ color: '#62636A' }}>Maintenance - Bay 1</span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#A0A2A8', fontSize: '0.55rem' }}>15:30</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.62rem', fontFamily: "'Inter', sans-serif" }}>
                  <span style={{ color: '#72856C', fontWeight: 700 }}>● PTW-0430</span>
                  <span style={{ color: '#62636A' }}>Electrical - Bay 2</span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#A0A2A8', fontSize: '0.55rem' }}>14:45</span>
                </div>
              </div>
              <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.62rem', color: '#2C2D30', fontWeight: 700, cursor: 'pointer' }}>
                View all permits →
              </div>
            </div>

            {/* Card 4: Live Metrics */}
            <div style={{
              background: '#FFFFFF',
              border: '1px solid #E9E9E5',
              borderRadius: '8px',
              padding: '14px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.55rem', color: '#8E9096', letterSpacing: '0.08em', fontWeight: 800 }}>
                LIVE METRICS (BAY 3)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', margin: '4px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.62rem', fontFamily: "'Inter', sans-serif" }}>
                  <span style={{ color: '#62636A' }}>H₂S Level</span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#D9534F', fontWeight: 700 }}>{h2s?.value ?? 5.2} ppm</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.62rem', fontFamily: "'Inter', sans-serif" }}>
                  <span style={{ color: '#62636A' }}>O₂ Level</span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#D9534F', fontWeight: 700 }}>21.8 %</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.62rem', fontFamily: "'Inter', sans-serif" }}>
                  <span style={{ color: '#62636A' }}>Temperature</span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#2C2D30', fontWeight: 700 }}>{temp?.value ?? 38.6} °C</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.62rem', fontFamily: "'Inter', sans-serif" }}>
                  <span style={{ color: '#62636A' }}>Pressure</span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#2C2D30', fontWeight: 700 }}>{press?.value ?? 3.8} barg</span>
                </div>
              </div>
              <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.62rem', color: '#2C2D30', fontWeight: 700, cursor: 'pointer' }}>
                View all metrics →
              </div>
            </div>
          </div>
        </div>

        {/* Right Compound Risk Evidence Drawer (380px wide) */}
        <EvidencePanel />
        <AuthorizationOverlay />
        <DemoOverlays />
      </div>

      <NovaPresenceIndicator />
    </div>
  )
}

function SimulationLanding({ onStart }: { onStart: () => void }) {
  return (
    <div style={{
      width: '100vw',
      height: '100vh',
      background: '#F7F6F2',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: 'linear-gradient(rgba(200,201,198,0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(200,201,198,0.2) 1px, transparent 1px)',
        backgroundSize: '80px 80px',
        pointerEvents: 'none',
      }} />

      <div style={{
        textAlign: 'center',
        position: 'relative',
        zIndex: 2,
        animation: 'fade-up 0.8s ease both',
      }}>
        <div style={{
          width: 80,
          height: 80,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(217,83,79,0.15) 0%, rgba(217,83,79,0.02) 70%)',
          border: '2px solid rgba(217,83,79,0.3)',
          margin: '0 auto 32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          animation: 'pulse-ring 3s ease-in-out infinite',
          boxShadow: '0 0 40px rgba(217,83,79,0.15)',
        }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: '#D9534F',
            boxShadow: '0 0 20px rgba(217,83,79,0.4)',
          }} />
        </div>

        <div style={{
          fontFamily: "'Bebas Neue', sans-serif",
          fontSize: '3.8rem',
          color: '#0E0D1F',
          letterSpacing: '0.12em',
          lineHeight: 0.9,
          marginBottom: '8px',
        }}>
          LIVE SYSTEM SIMULATION
        </div>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.6rem',
          color: '#D9534F',
          letterSpacing: '0.2em',
          textTransform: 'uppercase',
          marginBottom: '32px',
          fontWeight: 700,
        }}>
          NON-SCRIPTED AUTONOMOUS AI AGENT SYSTEM
        </div>

        <div style={{
          fontFamily: "'Titillium Web', sans-serif",
          fontSize: '0.95rem',
          color: '#62636A',
          maxWidth: '440px',
          margin: '0 auto 40px',
          lineHeight: 1.6,
          fontWeight: 400,
        }}>
          Real 2-second telemetry stream with autonomous AI agent intelligence. Nova speaks out loud when telemetry breaches critical thresholds and answers any real question asked into your microphone.
        </div>

        <button
          onClick={onStart}
          style={{
            fontFamily: "'Titillium Web', sans-serif",
            fontWeight: 700,
            fontSize: '0.85rem',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            background: '#D9534F',
            color: '#FFFFFF',
            border: 'none',
            padding: '16px 48px',
            borderRadius: '50px',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            boxShadow: '0 4px 14px rgba(217,83,79,0.3)',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translateY(-3px)'
            e.currentTarget.style.boxShadow = '0 8px 24px rgba(217,83,79,0.4)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = '0 4px 14px rgba(217,83,79,0.3)'
          }}
        >
          Launch Live Simulation
        </button>
      </div>
    </div>
  )
}

function NovaLogoSmall() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{
        width: 24,
        height: 24,
        borderRadius: '50%',
        background: '#0E0D1F',
        color: '#FFFFFF',
        fontFamily: "'Inter', sans-serif",
        fontWeight: 800,
        fontSize: '0.75rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        N
      </div>
      <span style={{
        fontFamily: "'Inter', sans-serif",
        fontWeight: 800,
        fontSize: '1rem',
        color: '#0E0D1F',
        letterSpacing: '0.08em',
      }}>
        NOVA
      </span>
    </div>
  )
}
