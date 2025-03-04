import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true); // Add loading state

    const loadUser = async () => {
        setLoading(true); // Start loading
        try {
            // First check if we have a user in localStorage
            const storedUser = localStorage.getItem('user');
            if (storedUser) {
                setUser(JSON.parse(storedUser));
                setIsAuthenticated(true);
            }
            
            // Then verify with the server
            const response = await axios.get('http://localhost:8080/me');
            setUser(response.data);
            setIsAuthenticated(true);
            localStorage.setItem('user', JSON.stringify(response.data));
        } catch (err) {
            console.error("Authentication error:", err);
            setUser(null);
            setIsAuthenticated(false);
            localStorage.removeItem('user');
        } finally {
            setLoading(false); // End loading regardless of outcome
        }
    }

    useEffect(() => {
        loadUser();
    }, []);

    const login = async (username, password) => {
        try {
            const response = await axios.post('http://localhost:8080/login', { username, password });
            setUser(response.data);
            setIsAuthenticated(true);
            localStorage.setItem('user', JSON.stringify(response.data));
            return response.data;
        } catch (error) {
            throw error;
        }
    };

    const register = async (username, email, password) => {
        try {
            const response = await axios.post('http://localhost:8080/register', { username, email, password });
            return response.data;
        } catch (error) {
            throw error;
        }
    };

    const logout = async () => {
        try {
            await axios.post('http://localhost:8080/logout');
            setUser(null);
            setIsAuthenticated(false);
            localStorage.removeItem('user');
        } catch (error) {
            console.error('Logout error:', error);
        }
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, user, loading, login, logout, register }}>
            {children}
        </AuthContext.Provider>
    );
};
