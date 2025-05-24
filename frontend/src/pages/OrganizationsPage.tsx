// src/pages/OrganizationsPage.tsx
import { useEffect, useState } from 'react';
import apiClient from '@/services/apiClient';
import { Organization, OrganizationSummary } from '@/types';
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import OrganizationForm from '@/components/organizations/OrganizationForm';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  // AlertDialogTrigger, // We trigger it programmatically
} from "@/components/ui/alert-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"; // Import Card components
import { MoreHorizontal, PlusCircle, Edit2Icon, Trash2Icon, EyeIcon } from "lucide-react";
import { useOrg } from '@/contexts/OrgContext'; // Assuming this is used for isLoadingActiveOrg
import { toast } from 'sonner';

const OrganizationsPage = () => {
  const [organizations, setOrganizations] = useState<OrganizationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true); // For fetching organizations list
  const [error, setError] = useState<string | null>(null);
  
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [currentOrganization, setCurrentOrganization] = useState<Organization | undefined>(undefined);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [orgToDelete, setOrgToDelete] = useState<OrganizationSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const { refreshUserOrganizations, isLoading: isLoadingActiveOrg } = useOrg(); // Assuming isLoadingActiveOrg is from OrgContext

  const fetchOrganizations = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<OrganizationSummary[]>('/organizations/');
      setOrganizations(response.data);
    } catch (err: any) {
      console.error("Failed to fetch organizations:", err);
      setError(err.response?.data?.detail || 'Failed to load organizations.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganizations();
  }, []);

  const handleOpenCreateModal = () => {
    setFormMode('create');
    setCurrentOrganization(undefined);
    setIsFormModalOpen(true);
  };

  const handleOpenEditModal = async (orgId: string) => {
    setFormMode('edit');
    try {
      const response = await apiClient.get<Organization>(`/organizations/${orgId}`);
      setCurrentOrganization(response.data);
      setIsFormModalOpen(true);
    } catch (err: any) {
      console.error("Failed to fetch organization details for edit:", err);
      toast.error(err.response?.data?.detail || "Failed to load organization details. Please try again.");
    }
  };

  const handleFormSuccess = async (processedOrganization: Organization) => {
    fetchOrganizations();
    await refreshUserOrganizations();
    setIsFormModalOpen(false);
    toast.success(`Organization "${processedOrganization.name}" ${formMode === 'create' ? 'created' : 'updated'} successfully!`);
  };

  const openDeleteConfirmDialog = (org: OrganizationSummary) => {
    setOrgToDelete(org);
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!orgToDelete) return;
    setIsDeleting(true);
    setError(null);
    try {
      await apiClient.delete(`/organizations/${orgToDelete.id}`);
      setOrganizations(prevOrgs => prevOrgs.filter(o => o.id !== orgToDelete.id));
      await refreshUserOrganizations();
      // fetchOrganizations(); // Re-fetching after optimistic update + refresh might be redundant
      toast.success(`Organization "${orgToDelete.name}" deleted successfully.`);
    } catch (err: any) {
      console.error("Failed to delete organization:", err);
      setError(err.response?.data?.detail || "Failed to delete organization.");
      toast.error(err.response?.data?.detail || "Failed to delete organization.");
    } finally {
      setIsDeleting(false);
      setIsDeleteDialogOpen(false);
      setOrgToDelete(null);
    }
  };

  // This assumes isLoadingActiveOrg is relevant for this page, similar to CustomersPage
  if (isLoadingActiveOrg) {
    return <div className="container mx-auto px-4 py-10 text-center">Loading organization context...</div>;
  }

  if (isLoading && organizations.length === 0) {
    return <div className="container mx-auto px-4 py-10 text-center">Loading organizations...</div>;
  }
  
  if (error && organizations.length === 0) {
    return (
      <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        <div className="flex justify-between items-center">
            <h1 className="text-2xl sm:text-3xl font-bold">Organizations</h1>
             {/* Optionally show create button even on error */}
        </div>
        <Card className="w-full">
            <CardHeader>
                <CardTitle>Manage Organizations</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="text-center py-10 text-destructive">{error}</div>
            </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <h1 className="text-2xl sm:text-3xl font-bold">Organizations</h1>
            <Dialog open={isFormModalOpen} onOpenChange={setIsFormModalOpen}>
                <DialogTrigger asChild>
                    <Button onClick={handleOpenCreateModal}>
                        <PlusCircle className="mr-2 h-4 w-4" /> Create Organization
                    </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[525px]">
                    <DialogHeader>
                        <DialogTitle>{formMode === 'create' ? 'Create New Organization' : 'Edit Organization'}</DialogTitle>
                        <DialogDescription>
                            {formMode === 'create' 
                            ? "Fill in the details for your new organization." 
                            : `Editing organization: ${currentOrganization?.name || ''}`}
                        </DialogDescription>
                    </DialogHeader>
                     {isFormModalOpen && (formMode === 'create' || (formMode === 'edit' && currentOrganization)) && (
                        <OrganizationForm
                            mode={formMode}
                            initialData={currentOrganization}
                            onSuccess={handleFormSuccess}
                            onCancel={() => setIsFormModalOpen(false)}
                        />
                    )}
                </DialogContent>
            </Dialog>
        </div>

        <Card className="w-full">
            <CardHeader>
                {/* <CardTitle>Your Organizations</CardTitle> */}
                {/* Error specific to table data, shown if list might be partially loaded or after an action error */}
                {error && <p className="text-sm text-destructive py-2 px-1 text-center">{error}</p>}
            </CardHeader>
            <CardContent>
                {!isLoading && organizations.length === 0 && !error ? (
                     <div className="text-center py-10 border-2 border-dashed border-muted rounded-lg">
                        <h3 className="text-xl font-semibold mb-2">No Organizations Yet</h3>
                        <p className="text-muted-foreground mb-4">Get started by creating your first organization.</p>
                        <Button onClick={handleOpenCreateModal} size="lg">
                            <PlusCircle className="mr-2 h-5 w-5" /> Create Organization
                        </Button>
                    </div>
                ) : (
                <div className="rounded-md border"> {/* Added border around table for consistency if not part of Table itself */}
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead className="w-[80px] sm:w-[100px]">Logo</TableHead>
                                <TableHead>Name</TableHead>
                                <TableHead className="hidden sm:table-cell">Contact Email</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {organizations.map((org) => (
                                <TableRow key={org.id}>
                                <TableCell>
                                    {org.logo_url ? (
                                    <img src={org.logo_url} alt={`${org.name} logo`} className="h-10 w-10 object-contain rounded-sm bg-accent p-0.5" />
                                    ) : (
                                    <div className="h-10 w-10 bg-muted rounded-sm flex items-center justify-center text-muted-foreground text-xs">
                                        
                                    </div>
                                    )}
                                </TableCell>
                                <TableCell className="font-medium">{org.name}</TableCell>
                                <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                                    {/* Assuming OrganizationSummary includes contact_email or using type assertion */}
                                    {(org as Organization).contact_email || 'N/A'}
                                </TableCell> 
                                <TableCell className="text-right">
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" className="h-8 w-8 p-0"><MoreHorizontal className="h-4 w-4" /></Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                            <DropdownMenuItem onClick={() => alert(`View details for ${org.name}`)} className="cursor-pointer">
                                                <EyeIcon className="mr-2 h-4 w-4" /> View Details
                                            </DropdownMenuItem>
                                            <DropdownMenuItem onClick={() => handleOpenEditModal(org.id)} className="cursor-pointer">
                                                <Edit2Icon className="mr-2 h-4 w-4" />Edit
                                            </DropdownMenuItem>
                                            <DropdownMenuSeparator />
                                            <DropdownMenuItem 
                                                onClick={() => openDeleteConfirmDialog(org)} 
                                                className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer">
                                                <Trash2Icon className="mr-2 h-4 w-4" />Delete
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
                )}
                {/* Loading indicator for subsequent fetches */}
                {isLoading && organizations.length > 0 && (
                     <div className="text-center py-4 text-sm text-muted-foreground">Refreshing organizations...</div>
                )}
            </CardContent>
        </Card>
        
        <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                    <AlertDialogDescription>
                    This action cannot be undone. This will permanently delete the
                    organization "<strong>{orgToDelete?.name || ''}</strong>" and all its associated data (customers, items, invoices, etc.).
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel onClick={() => { setOrgToDelete(null); setIsDeleteDialogOpen(false); }}>Cancel</AlertDialogCancel>
                    <AlertDialogAction 
                    onClick={handleConfirmDelete}
                    disabled={isDeleting} 
                    className="bg-destructive hover:bg-destructive/90 text-white"
                    >
                    {isDeleting ? "Deleting..." : "Yes, delete organization"}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    </div>
  );
};

export default OrganizationsPage;