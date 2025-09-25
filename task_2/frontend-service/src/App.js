import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000';

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await axios.get(`${API_BASE_URL}/api/users`);
      setUsers(response.data.users || []);
    } catch (err) {
      setError('Failed to fetch users');
      console.error('Error fetching users:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Microservices Dashboard</h1>
        
        <div className="users-section">
          <h2>Users</h2>
          <button onClick={fetchUsers} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh Users'}
          </button>
          
          {error && <div className="error">{error}</div>}
          
          <div className="users-list">
            {users.length > 0 ? (
              users.map((user, index) => (
                <div key={user.id || index} className="user-item">
                  <strong>{user.name}</strong> - {user.email}
                </div>
              ))
            ) : (
              <p>No users found</p>
            )}
          </div>
        </div>
      </header>
    </div>
  );
}

export default App;