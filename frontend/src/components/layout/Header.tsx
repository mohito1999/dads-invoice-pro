// src/components/layout/Header.tsx
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuGroup, // For grouping items
} from "@/components/ui/dropdown-menu";
import { Building, ChevronsUpDown, PlusCircle } from "lucide-react"; // Icons
import { useAuth } from "@/contexts/AuthContext"; // To get user
import { useOrg } from "@/contexts/OrgContext"; // To get orgs and active org
// import { Avatar, AvatarFallback, AvatarImage } ... (other imports for future)

const Header = () => {
  const { user } = useAuth(); // Get current user
  const { 
    activeOrganization, 
    setActiveOrganization, 
    userOrganizations, 
    isLoadingOrgs 
  } = useOrg();

  // Placeholder for user name display
  const userName = user?.full_name || user?.email || "User";

  return (
    <header className="sticky top-0 z-30 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 max-w-screen-2xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Left Section: Org Switcher + App Name */}
        <div className="flex items-center gap-6">
          {/* Organization Switcher Dropdown */}
          {userOrganizations.length > 0 ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2 px-3">
                  <Building className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm font-medium text-foreground truncate max-w-[150px] sm:max-w-[200px]">
                    {activeOrganization ? activeOrganization.name : "Select Organization"}
                  </span>
                  <ChevronsUpDown className="ml-auto h-4 w-4 shrink-0 opacity-50" />
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
                      {/* Add org logo here if available: <img src={org.logo_url} ... /> */}
                      {org.name}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                {/* Link to Organizations page to create/manage */}
                <DropdownMenuItem asChild className="cursor-pointer">
                  <Link to="/organizations">
                    <PlusCircle className="mr-2 h-4 w-4" />
                    Manage Organizations
                  </Link>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
             // If no organizations, link to create one or show app name
             <Link to={userOrganizations.length === 0 && user ? "/organizations" : "/"} className="flex items-center gap-2">
                 <Building className="h-5 w-5 text-primary" />
                 <span className="text-lg font-semibold text-foreground">
                     Invoice Pro
                 </span>
             </Link>
          )}
          
          {/* Desktop Navigation Links - Conditionally render if an org is selected? */}
          {activeOrganization && (
             <nav className="hidden items-center gap-5 text-sm font-medium md:flex">
                 <Link to="/" className="text-muted-foreground transition-colors hover:text-foreground">Dashboard</Link>
                 <Link to="/customers" className="text-muted-foreground transition-colors hover:text-foreground">Customers</Link>
                 <Link to="/items" className="text-muted-foreground transition-colors hover:text-foreground">Items</Link>
                 <Link to="/invoices" className="text-muted-foreground transition-colors hover:text-foreground">Invoices</Link>
             </nav>
          )}
        </div>

        {/* Right Section: User Menu */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm"> {userName} </Button> {/* Simplified user display */}
          {/* User DropdownMenu placeholder would go here */}
        </div>
      </div>
    </header>
  );
};

export default Header;