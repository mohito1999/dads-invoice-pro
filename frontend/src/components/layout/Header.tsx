// src/components/layout/Header.tsx
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuGroup,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Building, ChevronsUpDown, PlusCircle, UserCircle, LogOut, Settings, Menu as MenuIcon } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useOrg } from "@/contexts/OrgContext";
import { useState } from "react";

const Header = () => {
  const { user, logout } = useAuth();
  const { 
    activeOrganization, 
    setActiveOrganization, 
    userOrganizations 
  } = useOrg();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const getUserInitials = (name?: string | null, email?: string | null): string => {
     if (name) {
         const parts = name.split(' ');
         if (parts.length > 1) {
             return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
         }
         return name.substring(0, 2).toUpperCase();
     }
     if (email) {
         return email.substring(0, 2).toUpperCase();
     }
     return "U";
  };

  const userNameDisplay = user?.full_name || user?.email || "User";
  const userEmailDisplay = user?.email || "";

  const commonNavLinks = (isMobile: boolean = false) => (
     <>
         <Link 
             to="/" 
             className={isMobile ? "block py-2 text-lg hover:bg-muted rounded-md px-2" : "text-muted-foreground transition-colors hover:text-foreground"}
             onClick={() => isMobile && setIsMobileMenuOpen(false)}
         >
             Dashboard
         </Link>
         <Link 
             to="/organizations" 
             className={isMobile ? "block py-2 text-lg hover:bg-muted rounded-md px-2" : "text-muted-foreground transition-colors hover:text-foreground"}
             onClick={() => isMobile && setIsMobileMenuOpen(false)}
         >
             Organizations
         </Link>
         {activeOrganization && (
             <>
                 <Link 
                     to="/customers" 
                     className={isMobile ? "block py-2 text-lg hover:bg-muted rounded-md px-2" : "text-muted-foreground transition-colors hover:text-foreground"}
                     onClick={() => isMobile && setIsMobileMenuOpen(false)}
                 >
                     Customers
                 </Link>
                 <Link 
                     to="/items" 
                     className={isMobile ? "block py-2 text-lg hover:bg-muted rounded-md px-2" : "text-muted-foreground transition-colors hover:text-foreground"}
                     onClick={() => isMobile && setIsMobileMenuOpen(false)}
                 >
                     Items
                 </Link>
                 <Link 
                     to="/invoices" 
                     className={isMobile ? "block py-2 text-lg hover:bg-muted rounded-md px-2" : "text-muted-foreground transition-colors hover:text-foreground"}
                     onClick={() => isMobile && setIsMobileMenuOpen(false)}
                 >
                     Invoices
                 </Link>
             </>
         )}
     </>
  );

  return (
    <header className="sticky top-0 z-30 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 max-w-screen-2xl items-center justify-between px-4 sm:px-6 lg:px-8">
        
        {/* Left Section: Mobile Menu, Org Switcher/App Name, AND Desktop Nav */}
        <div className="flex flex-1 items-center gap-2 md:gap-4 lg:gap-6"> {/* Reduced gap slightly, flex-1 to allow nav to take space */}
          {/* Mobile Menu Trigger */}
          {user && (
             <div className="md:hidden">
                 <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
                 <SheetTrigger asChild>
                     <Button variant="ghost" size="icon">
                     <MenuIcon className="h-6 w-6" />
                     <span className="sr-only">Toggle Menu</span>
                     </Button>
                 </SheetTrigger>
                 <SheetContent side="left" className="w-72 sm:w-80 pt-10">
                     <SheetHeader className="mb-6 text-center">
                         <SheetTitle className="text-xl">
                             {activeOrganization ? activeOrganization.name : "Invoice Pro"}
                         </SheetTitle>
                     </SheetHeader>
                     <nav className="grid gap-3 px-2">
                         {commonNavLinks(true)}
                     </nav>
                 </SheetContent>
                 </Sheet>
             </div>
          )}

          {/* Organization Switcher / App Name */}
          {userOrganizations.length > 0 && user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2 px-3 hover:bg-accent focus-visible:ring-ring focus-visible:ring-1 focus-visible:ring-offset-1">
                  <Building className="h-5 w-5 text-muted-foreground" />
                  <span className="text-base font-medium text-foreground truncate max-w-[150px] sm:max-w-[200px] md:max-w-[250px]"> {/* Changed to text-base, adjusted max-width */}
                    {activeOrganization ? activeOrganization.name : "Select Organization"}
                  </span>
                  <ChevronsUpDown className="ml-1 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-64" align="start">
                <DropdownMenuLabel>Switch Organization</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  {userOrganizations.map((org) => (
                    <DropdownMenuItem
                      key={org.id}
                      onClick={() => setActiveOrganization(org)}
                      className={`cursor-pointer ${activeOrganization?.id === org.id ? 'bg-accent text-accent-foreground' : ''}`}
                    >
                      {org.name}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild className="cursor-pointer">
                  <Link to="/organizations">
                    <PlusCircle className="mr-2 h-4 w-4" />
                    Manage Organizations
                  </Link>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
           ) : (
             <Link to={user ? "/organizations" : "/"} className="flex items-center gap-2">
                 <Building className="h-5 w-5 text-primary" />
                 <span className="text-lg font-semibold text-foreground"> {/* Kept text-lg for app name */}
                     Invoice Pro
                 </span>
             </Link>
           )
          }

          {/* Desktop Navigation Links (Moved here) */}
          {user && (
           <nav className="hidden items-center gap-4 lg:gap-5 text-base font-medium md:flex md:ml-4 lg:ml-6"> {/* Changed to text-base, added md:ml-4/lg:ml-6, adjusted gap */}
               {commonNavLinks(false)}
           </nav>
          )}
        </div>


        {/* Right Section: User Menu */}
        {user && (
         <div className="flex items-center gap-4">
             <DropdownMenu>
                 <DropdownMenuTrigger asChild>
                 <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                     <Avatar className="h-9 w-9">
                     <AvatarFallback>{getUserInitials(user.full_name, user.email)}</AvatarFallback>
                     </Avatar>
                 </Button>
                 </DropdownMenuTrigger>
                 <DropdownMenuContent className="w-56" align="end" forceMount>
                 <DropdownMenuLabel className="font-normal">
                     <div className="flex flex-col space-y-1">
                     <p className="text-sm font-medium leading-none">{userNameDisplay}</p>
                     <p className="text-xs leading-none text-muted-foreground">
                         {userEmailDisplay}
                     </p>
                     </div>
                 </DropdownMenuLabel>
                 <DropdownMenuSeparator />
                 <DropdownMenuGroup>
                     <DropdownMenuItem className="cursor-pointer" onClick={() => alert("Profile page not yet implemented")}>
                         <UserCircle className="mr-2 h-4 w-4" />
                         <span>Profile</span>
                     </DropdownMenuItem>
                     <DropdownMenuItem className="cursor-pointer" onClick={() => alert("Settings page not yet implemented")}>
                         <Settings className="mr-2 h-4 w-4" />
                         <span>Settings</span>
                     </DropdownMenuItem>
                 </DropdownMenuGroup>
                 <DropdownMenuSeparator />
                 <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-red-600 focus:text-red-600 focus:bg-red-50">
                     <LogOut className="mr-2 h-4 w-4" />
                     <span>Log out</span>
                 </DropdownMenuItem>
                 </DropdownMenuContent>
             </DropdownMenu>
         </div>
        )}
      </div>
    </header>
  );
};

export default Header;