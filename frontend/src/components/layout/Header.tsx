// src/components/layout/Header.tsx
import { Link, useNavigate } from "react-router-dom"; // Import useNavigate
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
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Building, ChevronsUpDown, PlusCircle, UserCircle, LogOut, Settings } from "lucide-react"; // Added UserCircle, LogOut, Settings
import { useAuth } from "@/contexts/AuthContext";
import { useOrg } from "@/contexts/OrgContext";

const Header = () => {
  const { user, logout } = useAuth(); // Get user and logout function
  const { 
    activeOrganization, 
    setActiveOrganization, 
    userOrganizations, 
    // isLoadingOrgs // Not used directly here for now
  } = useOrg();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout(); // Call logout from AuthContext
    navigate("/login"); // Redirect to login page
  };

  // Determine user initials for AvatarFallback
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
     return "U"; // Default User
  };

  const userNameDisplay = user?.full_name || user?.email || "User";
  const userEmailDisplay = user?.email || "";

  return (
    <header className="sticky top-0 z-30 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 max-w-screen-2xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Left Section: Org Switcher + App Name */}
        <div className="flex items-center gap-6">
          {userOrganizations.length > 0 && user ? ( // Only show switcher if user is logged in and has orgs
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2 px-3 hover:bg-accent focus-visible:ring-ring focus-visible:ring-1 focus-visible:ring-offset-1">
                  <Building className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm font-medium text-foreground truncate max-w-[150px] sm:max-w-[200px]">
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
             <Link to={user ? "/organizations" : "/"} className="flex items-center gap-2"> {/* If no orgs but logged in, go to org page */}
                 <Building className="h-5 w-5 text-primary" />
                 <span className="text-lg font-semibold text-foreground">
                     Invoice Pro
                 </span>
             </Link>
          )}
          
          {activeOrganization && user && ( // Only show main nav if user logged in and org selected
             <nav className="hidden items-center gap-5 text-sm font-medium md:flex">
                 <Link to="/" className="text-muted-foreground transition-colors hover:text-foreground">Dashboard</Link>
                 <Link to="/customers" className="text-muted-foreground transition-colors hover:text-foreground">Customers</Link>
                 <Link to="/items" className="text-muted-foreground transition-colors hover:text-foreground">Items</Link>
                 <Link to="/invoices" className="text-muted-foreground transition-colors hover:text-foreground">Invoices</Link>
             </nav>
          )}
        </div>

        {/* Right Section: User Menu */}
        {user && ( // Only show user menu if user is logged in
         <div className="flex items-center gap-4">
             <DropdownMenu>
                 <DropdownMenuTrigger asChild>
                 <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                     <Avatar className="h-9 w-9">
                     {/* <AvatarImage src={user.avatarUrl || undefined} alt={userNameDisplay} /> Placeholder for actual avatar */}
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