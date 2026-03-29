import React, { useState } from 'react';
import { evaluateBill } from '../api';
import './Simulator.css';

export default function Simulator({ userId }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [goals, setGoals] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;

    setLoading(true);
    setReport(null);
    setError('');

    try {
      const response = await evaluateBill(title, description, goals);
      setReport(response);
    } catch (err) {
      setError(err.message || 'Failed to submit bill. Please check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  const isOpposed = report?.verdict?.toLowerCase().includes('oppose');

  return (
    <div className="simulator-container">
      <div className="simulator-header">
        <h1>🏛️ Parliamentary Simulator</h1>
        <p>Draft a bill and defend it against the AI Opposition.</p>
      </div>

      <div className="simulator-content">
        {/* Left Side: Drafting Desk */}
        <div className="drafting-desk">
          <h2>Drafting Desk</h2>
          <form className="draft-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="title">Bill Title</label>
              <input
                id="title"
                type="text"
                placeholder="e.g., The Mandatory Voting Act, 2025"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="description">Bill Description (What does it do?)</label>
              <textarea
                id="description"
                placeholder="Describe the rules, penalties, and implementation of your law..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="goals">Goals (Why are you proposing this?)</label>
              <textarea
                id="goals"
                placeholder="What societal problem are you trying to fix?"
                value={goals}
                onChange={(e) => setGoals(e.target.value)}
              />
            </div>

            <button type="submit" className="btn-submit-bill" disabled={loading || !title || !description}>
              {loading ? 'Presenting to the House...' : 'Introduce Bill'}
            </button>
            {error && <div style={{color: 'red', marginTop: '1rem'}}>{error}</div>}
          </form>
        </div>

        {/* Right Side: Opposition Report */}
        <div className="opposition-report">
          <h2>Opposition Review</h2>
          
          {!loading && !report && (
            <div style={{color: 'var(--text-muted)', textAlign: 'center', marginTop: '3rem'}}>
              Prepare your bill and submit it. The Leader of the Opposition will analyze it for constitutional conflicts, practical flaws, and unintended consequences.
            </div>
          )}

          {loading && (
            <div className="loading-state">
              <div className="spinner"></div>
              <div>The Opposition is analyzing your bill...</div>
            </div>
          )}

          {report && (
            <div className="report-content">
              <div className={`verdict-banner ${isOpposed ? 'oppose' : 'support'}`}>
                Verdict: {report.verdict}
              </div>

              <div className="report-section">
                <h3>📜 Speech to the House</h3>
                <p>"{report.speech}"</p>
              </div>

              {report.constitutional_issues && report.constitutional_issues.length > 0 && (
                <div className="report-section">
                  <h3>⚖️ Constitutional Concerns</h3>
                  <ul>
                    {report.constitutional_issues.map((issue, i) => <li key={i}>{issue}</li>)}
                  </ul>
                </div>
              )}

              {report.practical_flaws && report.practical_flaws.length > 0 && (
                <div className="report-section">
                  <h3>🏗️ Practical Flaws</h3>
                  <ul>
                    {report.practical_flaws.map((flaw, i) => <li key={i}>{flaw}</li>)}
                  </ul>
                </div>
              )}

              {report.amendment_suggestions && report.amendment_suggestions.length > 0 && (
                <div className="report-section">
                  <h3>💡 Suggested Amendments</h3>
                  <ul>
                    {report.amendment_suggestions.map((suggestion, i) => <li key={i}>{suggestion}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
