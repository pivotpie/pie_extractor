import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";

interface AuthGuardProps {
  children: React.ReactNode;
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const navigate = useNavigate();

  useEffect(() => {
    const isAuthenticated = localStorage.getItem("pie_extractor_auth");
    if (!isAuthenticated) {
      navigate("/login");
    }
  }, [navigate]);

  const isAuthenticated = localStorage.getItem("pie_extractor_auth");
  
  if (!isAuthenticated) {
    return null; // or a loading spinner
  }

  return <>{children}</>;
};

export default AuthGuard;