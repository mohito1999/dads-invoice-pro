// frontend/vite.config.ts
import path from "path"; // Node.js path module
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite'; // Your Tailwind Vite plugin
// https://vite.dev/config/
export default defineConfig({
    plugins: [
        react(),
        tailwindcss()
    ],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"), // Maps "@" to your "./src" directory
        },
    },
});
