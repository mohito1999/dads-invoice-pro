// src/components/layout/MainLayout.tsx
import { Outlet } from "react-router-dom";
import Header from "./Header";

const MainLayout = () => {
  return (
    <div className="flex min-h-screen flex-col bg-muted/40"> {/* Overall page background */}
      <Header />
      {/* This div will now be the main scrollable content area below the sticky header */}
      <div className="flex-1 overflow-y-auto"> 
        <main className="container mx-auto max-w-screen-2xl px-4 sm:px-6 lg:px-8 py-6"> 
          {/* 
            - 'container mx-auto': Standard Tailwind for centering a fixed-width container.
            - 'max-w-screen-2xl': Limits the maximum width of the content.
            - 'px-4 sm:px-6 lg:px-8': Responsive horizontal padding.
            - 'py-6': Vertical padding for the content area.
          */}
          <Outlet /> {/* Child page components will render here */}
        </main>
      </div>
      {/* Maybe a footer here later */}
    </div>
  );
};
export default MainLayout;