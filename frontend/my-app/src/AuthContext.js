import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [user, setUser] = useState(null);

    const loadUser = async () => {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
            setUser(JSON.parse(storedUser));
            setIsAuthenticated(true);
        }
        try {
            const response = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/me`);
            setUser(response.data);
            setIsAuthenticated(true);
            localStorage.setItem('user', JSON.stringify(response.data));
        } catch (err) {
            setUser(null);
            setIsAuthenticated(false);
            localStorage.removeItem('user'); // Remove user from local storage if not authenticated.
            console.error("User not authenticated", err);
        }
    };

    useEffect(() => {
        loadUser();
    }, []);

    const login = async (username, password) => {
        try {
            const response = await axios.post(`${process.env.REACT_APP_API_BASE_URL}/login`, { username, password });
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
            const response = await axios.post(`${process.env.REACT_APP_API_BASE_URL}/register`, { username, email, password });
            return response.data;
        } catch (error) {
            throw error;
        }
    };

    const logout = async () => {
        try {
            await axios.post(`${process.env.REACT_APP_API_BASE_URL}/logout`);
            setUser(null);
            setIsAuthenticated(false);
            localStorage.removeItem('user');
        } catch (error) {
            console.error('Logout error:', error);
        }
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, user, login, logout, register }}>
            {children}
        </AuthContext.Provider>
    );
};
