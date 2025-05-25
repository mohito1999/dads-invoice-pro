// src/config/index.ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const getApiBaseUrl = (): string => {
    return API_BASE_URL;
};

// Function to construct full static URLs
export const getFullStaticUrl = (relativePath?: string | null): string | undefined => {
    if (!relativePath) {
        return undefined;
    }
    // Ensure relativePath starts with a slash if it's meant to be from the static root
    const path = relativePath.startsWith('/') ? relativePath : `/${relativePath}`;
    return `${getApiBaseUrl()}${path}`;
};