// src/contexts/OrgContext.tsx
import React, { createContext, useContext, useState, ReactNode, useEffect } from 'react';
import { OrganizationSummary } from '@/types'; // Assuming this type has id and name
import apiClient from '@/services/apiClient';
import { useAuth } from './AuthContext'; // To know if user is authenticated

interface OrgContextType {
  activeOrganization: OrganizationSummary | null;
  setActiveOrganization: (org: OrganizationSummary | null) => void;
  userOrganizations: OrganizationSummary[];
  isLoadingOrgs: boolean;
  refreshUserOrganizations: () => Promise<void>;
}

const OrgContext = createContext<OrgContextType | undefined>(undefined);

export const OrgProvider = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated, user } = useAuth(); // Get auth state
  const [activeOrganization, setActiveOrganizationState] = useState<OrganizationSummary | null>(null);
  const [userOrganizations, setUserOrganizations] = useState<OrganizationSummary[]>([]);
  const [isLoadingOrgs, setIsLoadingOrgs] = useState<boolean>(false);

  const setActiveOrganization = (org: OrganizationSummary | null) => {
    setActiveOrganizationState(org);
    if (org) {
      localStorage.setItem('activeOrganizationId', org.id); // Persist choice
    } else {
      localStorage.removeItem('activeOrganizationId');
    }
  };

  const fetchUserOrganizations = async () => {
    if (!isAuthenticated || !user) { // Only fetch if user is logged in
      setUserOrganizations([]);
      setActiveOrganizationState(null); // Clear active org if logged out
      localStorage.removeItem('activeOrganizationId');
      return;
    }
    setIsLoadingOrgs(true);
    try {
      const response = await apiClient.get<OrganizationSummary[]>('/organizations/');
      setUserOrganizations(response.data);

      // Attempt to restore active organization from localStorage or default to first
      const storedActiveOrgId = localStorage.getItem('activeOrganizationId');
      if (response.data.length > 0) {
        let currentActive = null;
        if (storedActiveOrgId) {
          currentActive = response.data.find(org => org.id === storedActiveOrgId) || null;
        }
        if (!currentActive) { // If stored not found or not set, default to first
          currentActive = response.data[0];
        }
        setActiveOrganizationState(currentActive); // Set without writing to localStorage again here
        if (currentActive && !storedActiveOrgId) { // If we defaulted, store it now
            localStorage.setItem('activeOrganizationId', currentActive.id);
        }

      } else {
        setActiveOrganizationState(null); // No orgs, so no active org
        localStorage.removeItem('activeOrganizationId');
      }
    } catch (error) {
      console.error("Failed to fetch user organizations:", error);
      setUserOrganizations([]); // Clear on error
      setActiveOrganizationState(null);
    } finally {
      setIsLoadingOrgs(false);
    }
  };
  
  useEffect(() => {
    fetchUserOrganizations();
  }, [isAuthenticated, user]); // Re-fetch when auth state changes

  const refreshUserOrganizations = async () => {
    await fetchUserOrganizations();
  };

  return (
    <OrgContext.Provider value={{ 
        activeOrganization, 
        setActiveOrganization, 
        userOrganizations, 
        isLoadingOrgs,
        refreshUserOrganizations 
    }}>
      {children}
    </OrgContext.Provider>
  );
};

export const useOrg = (): OrgContextType => {
  const context = useContext(OrgContext);
  if (context === undefined) {
    throw new Error('useOrg must be used within an OrgProvider');
  }
  return context;
};