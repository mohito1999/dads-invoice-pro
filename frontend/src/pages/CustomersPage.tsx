// src/pages/CustomersPage.tsx
import { useEffect, useState } from 'react';
import apiClient from '@/services/apiClient';
import { Customer, CustomerSummary } from '@/types';
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import CustomerForm from '@/components/customers/CustomerForm';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"; // Import Card components
import { MoreHorizontal, PlusCircle, Edit2Icon, Trash2Icon } from "lucide-react";
import { useOrg } from '@/contexts/OrgContext';
import { Link } from 'react-router-dom';

const CustomersPage = () => {
  const { activeOrganization, isLoadingOrgs: isLoadingActiveOrg } = useOrg();
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false); // For fetching customers list
  const [error, setError] = useState<string | null>(null);
  
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [currentCustomer, setCurrentCustomer] = useState<Customer | undefined>(undefined);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [customerToDelete, setCustomerToDelete] = useState<CustomerSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false); // Specific loading state for delete

  const fetchCustomers = async (orgId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<CustomerSummary[]>(`/customers/?organization_id=${orgId}`);
      setCustomers(response.data);
    } catch (err: any) {
      console.error("Failed to fetch customers:", err);
      setError(err.response?.data?.detail || 'Failed to load customers.');
      setCustomers([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (activeOrganization?.id) {
      fetchCustomers(activeOrganization.id);
    } else if (!isLoadingActiveOrg) {
      setCustomers([]);
      setError(null); // Clear errors if no org is active
    }
  }, [activeOrganization, isLoadingActiveOrg]);

  const handleOpenCreateModal = () => {
    setFormMode('create');
    setCurrentCustomer(undefined);
    setIsFormModalOpen(true);
  };

  const handleOpenEditModal = async (customerId: string) => {
    setFormMode('edit');
    try {
      const response = await apiClient.get<Customer>(`/customers/${customerId}`);
      setCurrentCustomer(response.data);
      setIsFormModalOpen(true);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to load customer details.");
    }
  };

  const handleFormSuccess = (processedCustomer: Customer) => {
    if (activeOrganization?.id) fetchCustomers(activeOrganization.id);
    setIsFormModalOpen(false);
    alert(`Customer "${processedCustomer.company_name}" ${formMode === 'create' ? 'created' : 'updated'} successfully!`);
  };

  const openDeleteConfirmDialog = (customer: CustomerSummary) => {
    setCustomerToDelete(customer);
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!customerToDelete || !activeOrganization?.id) return;
    setIsDeleting(true);
    setError(null);
    try {
      await apiClient.delete(`/customers/${customerToDelete.id}`);
      // Optimistic update:
      setCustomers(prevCustomers => prevCustomers.filter(c => c.id !== customerToDelete.id));
      // Or refetch: fetchCustomers(activeOrganization.id);
      alert(`Customer "${customerToDelete.company_name}" deleted successfully.`);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete customer.");
      alert(err.response?.data?.detail || "Failed to delete customer.");
    } finally {
      setIsDeleting(false);
      setIsDeleteDialogOpen(false);
      setCustomerToDelete(null);
    }
  };

  if (isLoadingActiveOrg) {
     return <div className="container mx-auto px-4 py-10 text-center">Loading organization context...</div>;
  }

  if (!activeOrganization) {
    return (
      <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        <div className="flex justify-between items-center">
            <h1 className="text-2xl sm:text-3xl font-bold">Customers</h1>
        </div>
        <Card className="w-full">
            <CardHeader>
                <CardTitle>No Active Organization</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="text-center py-10">
                    <p className="text-muted-foreground">Please select or create an active organization to manage customers.</p>
                    <Button asChild className="mt-4">
                    <Link to="/organizations">Go to Organizations</Link>
                    </Button>
                </div>
            </CardContent>
        </Card>
      </div>
    );
  }
  
  if (isLoading && customers.length === 0) { // Loading customers for an active org
     return (
        <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <h1 className="text-2xl sm:text-3xl font-bold">Customers for {activeOrganization.name}</h1>
                {/* Button can be disabled or hidden during load */}
            </div>
            <Card className="w-full">
                <CardHeader />
                <CardContent>
                    <div className="text-center py-10">Loading customers...</div>
                </CardContent>
            </Card>
        </div>
     );
  }

  return (
    <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-2xl sm:text-3xl font-bold">Customers for {activeOrganization.name}</h1>
        <Button onClick={handleOpenCreateModal}>
          <PlusCircle className="mr-2 h-4 w-4" /> Create Customer
        </Button>
      </div>

      <Dialog open={isFormModalOpen} onOpenChange={setIsFormModalOpen}>
        <DialogContent className="sm:max-w-[525px]">
          <DialogHeader>
            <DialogTitle>{formMode === 'create' ? 'Create New Customer' : 'Edit Customer'}</DialogTitle>
            <DialogDescription>
              {formMode === 'create' 
                ? `Adding customer to organization: ${activeOrganization.name}.` 
                : `Editing customer: ${currentCustomer?.company_name || ''}`}
            </DialogDescription>
          </DialogHeader>
           {isFormModalOpen && (formMode === 'create' || (formMode === 'edit' && currentCustomer)) && (
            <CustomerForm
                mode={formMode}
                initialData={currentCustomer}
                organizationId={activeOrganization.id} // Pass active org ID
                onSuccess={handleFormSuccess}
                onCancel={() => setIsFormModalOpen(false)}
            />
           )}
        </DialogContent>
      </Dialog>

      <Card className="w-full">
        <CardHeader>
            {/* Optional CardTitle, page title might be enough */}
            {/* <CardTitle>Customer List</CardTitle> */}
            {error && customers.length > 0 && ( // Show error as a notice if data is already present
                <p className="text-sm text-destructive py-2 px-1 text-center">{error}</p>
            )}
        </CardHeader>
        <CardContent>
            {error && customers.length === 0 && ( // Prominent error if list is empty due to error
                 <div className="text-center py-10 text-destructive">{error}</div>
            )}
            {!isLoading && customers.length === 0 && !error ? (
                <div className="text-center py-10 border-2 border-dashed border-muted rounded-lg">
                    <h3 className="text-xl font-semibold mb-2">No Customers Yet</h3>
                    <p className="text-muted-foreground mb-4">No customers found for {activeOrganization.name}. Add your first one!</p>
                    <Button onClick={handleOpenCreateModal} size="lg">
                        <PlusCircle className="mr-2 h-5 w-5" /> Create Customer
                    </Button>
                </div>
            ) : (
                !error && customers.length > 0 && ( // Only show table if no error and customers exist
                    <div className="rounded-md border">
                        <Table>
                        <TableHeader>
                            <TableRow>
                            <TableHead>Company Name</TableHead>
                            <TableHead className="hidden md:table-cell">POC Name</TableHead>
                            <TableHead className="hidden sm:table-cell">Email</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {customers.map((cust) => (
                            <TableRow key={cust.id}>
                                <TableCell className="font-medium">{cust.company_name}</TableCell>
                                <TableCell className="hidden md:table-cell">{cust.poc_name || 'N/A'}</TableCell>
                                <TableCell className="hidden sm:table-cell">{cust.email || 'N/A'}</TableCell>
                                <TableCell className="text-right">
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" className="h-8 w-8 p-0"><MoreHorizontal className="h-4 w-4" /></Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                    <DropdownMenuItem onClick={() => handleOpenEditModal(cust.id)} className="cursor-pointer"><Edit2Icon className="mr-2 h-4 w-4" />Edit</DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => openDeleteConfirmDialog(cust)} className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer"><Trash2Icon className="mr-2 h-4 w-4" />Delete</DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                                </TableCell>
                            </TableRow>
                            ))}
                        </TableBody>
                        </Table>
                    </div>
                )
            )}
            {isLoading && customers.length > 0 && ( // Loading indicator for subsequent refreshes
                <div className="text-center py-4 text-sm text-muted-foreground">Refreshing customers...</div>
            )}
        </CardContent>
      </Card>

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the customer "<strong>{customerToDelete?.company_name || ''}</strong>" and all associated data (e.g., invoices).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {setCustomerToDelete(null); setIsDeleteDialogOpen(false);}}>Cancel</AlertDialogCancel>
            <AlertDialogAction 
                onClick={handleConfirmDelete} 
                disabled={isDeleting}
                className="bg-destructive hover:bg-destructive/90 text-destructive-foreground"
            >
              {isDeleting ? "Deleting..." : "Yes, delete customer"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
export default CustomersPage;