// src/components/layout/MainLayout.tsx
import { Outlet } from "react-router-dom";
import Header from "./Header";
import { Toaster } from "@/components/ui/sonner";

const MainLayout = () => {
  return (
    <div className="flex min-h-screen flex-col bg-muted/40">
      <Header />
      <div className="flex-1 overflow-y-auto"> 
        <main className="container mx-auto max-w-screen-2xl px-4 sm:px-6 lg:px-8 py-6"> 
          <Outlet /> 
        </main>
      </div>
      <Toaster richColors position="bottom-right" /> {/* <--- ADD THE TOASTER INSTANCE */}
      {/* You can customize position, richColors, etc. */}
    </div>
  );
};
export default MainLayout;