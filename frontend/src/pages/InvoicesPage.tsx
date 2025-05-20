// src/pages/InvoicesPage.tsx
import { useEffect, useState, useMemo } from 'react'; // Added useMemo
import apiClient from '@/services/apiClient';
import { InvoiceSummary, InvoiceStatusEnum, InvoiceTypeEnum, CustomerSummary, OrganizationSummary } from '@/types'; // Assuming all types are correct
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"; // Assuming CardDescription might be used
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
// --- Import AlertDialog components ---
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
// --- End AlertDialog imports ---
import { MoreHorizontal, PlusCircle, Edit2Icon, Trash2Icon, FileTextIcon, DownloadIcon, RefreshCwIcon, EyeIcon, SendIcon, FilterIcon } from "lucide-react"; // Added more icons
import { useOrg } from '@/contexts/OrgContext';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from "@/components/ui/badge";
import { format, parseISO } from 'date-fns'; // For date formatting (already present but good to confirm)


// Helper to get badge variant based on status
const getStatusBadgeVariant = (status: InvoiceStatusEnum): "default" | "secondary" | "destructive" | "outline" => {
  switch (status) {
    case InvoiceStatusEnum.PAID: return "default";
    case InvoiceStatusEnum.PARTIALLY_PAID: return "secondary";
    case InvoiceStatusEnum.OVERDUE: return "destructive";
    case InvoiceStatusEnum.UNPAID: return "outline";
    case InvoiceStatusEnum.DRAFT: return "secondary"; // Changed DRAFT to secondary for better visibility
    case InvoiceStatusEnum.CANCELLED: return "destructive"; // Or 'outline' with gray text
    default: return "outline";
  }
};


const InvoicesPage = () => {
  const { activeOrganization, isLoadingOrgs: isLoadingActiveOrg } = useOrg();
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false); // For fetching invoices list
  const [error, setError] = useState<string | null>(null);

  // --- State for Delete Functionality ---
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [invoiceToDelete, setInvoiceToDelete] = useState<InvoiceSummary | null>(null); // Renamed
  const [isDeleting, setIsDeleting] = useState(false); // Specific loading state for delete action
  // --- End State for Delete ---


  const fetchInvoices = async (orgId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ organization_id: orgId, skip: "0", limit: "100" });
      const response = await apiClient.get<InvoiceSummary[]>(`/invoices/?${params.toString()}`);
      // console.log("Fetched Invoices Raw (from API response.data):", JSON.parse(JSON.stringify(response.data))); // Debugging for total_amount issue
      setInvoices(response.data);
    } catch (err: any) {
      console.error("Failed to fetch invoices:", err);
      setError(err.response?.data?.detail || 'Failed to load invoices.');
      setInvoices([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (activeOrganization?.id) {
      fetchInvoices(activeOrganization.id);
    } else if (!isLoadingActiveOrg) {
      setInvoices([]);
      // Optionally set error or a message if no org is active and page requires it
      // setError("No active organization selected to display invoices.");
    }
  }, [activeOrganization, isLoadingActiveOrg]);

  const handleCreateInvoice = () => {
     if (activeOrganization) {
         navigate(`/invoices/new?orgId=${activeOrganization.id}`);
     } else {
         alert("Please select an active organization first.");
     }
  };
  
  const handleEditInvoice = (invoiceId: string) => {
     navigate(`/invoices/edit/${invoiceId}`);
  };

  const handleDownloadPdf = async (invoiceId: string, invoiceNumber: string) => {
     try {
         const response = await apiClient.get(`/invoices/${invoiceId}/pdf`, {
             responseType: 'blob',
         });
         const blob = new Blob([response.data], { type: 'application/pdf' });
         const link = document.createElement('a');
         link.href = window.URL.createObjectURL(blob);
         link.download = `Invoice-${invoiceNumber.replace(/[\/\s]/g, '_')}.pdf`;
         document.body.appendChild(link);
         link.click();
         document.body.removeChild(link);
         window.URL.revokeObjectURL(link.href);
     } catch (err) {
         console.error("Failed to download PDF:", err);
         alert("Failed to download PDF.");
     }
  };
  
  const handleTransformToCommercial = async (invoiceId: string) => {
     if(!confirm("This will create a new Commercial Invoice based on this Pro Forma. Continue?")) return;
     try {
         const response = await apiClient.post(`/invoices/${invoiceId}/transform-to-commercial`);
         alert(`Successfully transformed to Commercial Invoice: ${response.data.invoice_number}`);
         if(activeOrganization?.id) fetchInvoices(activeOrganization.id);
     } catch (err: any) {
         alert(err.response?.data?.detail || "Failed to transform invoice.");
     }
  };

  // --- Delete Handlers with Debugging ---
  const openDeleteConfirmDialog = (invToDelete: InvoiceSummary) => {
    console.log("DEBUG: openDeleteConfirmDialog called for invoice:", invToDelete);
    setInvoiceToDelete(invToDelete);
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    console.log("DEBUG: handleConfirmDelete attempting for:", invoiceToDelete);
    if (!invoiceToDelete) {
      console.log("DEBUG: No invoiceToDelete set, exiting handleConfirmDelete.");
      return;
    }
    
    console.log(`DEBUG: Would call API: DELETE /invoices/${invoiceToDelete.id}`);
    
    setIsDeleting(true); // Set loading state for delete action
    setError(null); // Clear previous errors

    // Actual delete logic (uncomment after basic console logs and dialog flow work)
    try {
      await apiClient.delete(`/invoices/${invoiceToDelete.id}`);
      setInvoices(prevInvoices => prevInvoices.filter(i => i.id !== invoiceToDelete.id)); // Optimistic update
      alert(`Invoice "${invoiceToDelete.invoice_number}" deleted successfully.`);
    } catch (err: any) {
      console.error("Failed to delete invoice:", err);
      const errorMsg = err.response?.data?.detail || "Failed to delete invoice.";
      setError(errorMsg); // Set error state to display to user
      alert(errorMsg); // Also alert for immediate feedback
    } finally {
      setIsDeleting(false); // Reset delete loading state
      setIsDeleteDialogOpen(false);
      setInvoiceToDelete(null);
    }
    

    // For initial testing of dialog flow (comment out the try/catch/finally block above when using this)
    // alert(`Simulated delete for invoice: ${invoiceToDelete.invoice_number}. API call commented out.`);
    // setIsDeleteDialogOpen(false);
    // setInvoiceToDelete(null);
    // setInvoices(prevInvoices => prevInvoices.filter(i => i.id !== invoiceToDelete!.id));
  };
  // --- End Delete Handlers ---


  if (isLoadingActiveOrg) return <div className="container mx-auto px-4 py-10 text-center">Loading organization context...</div>;
  
  if (!activeOrganization) {
    return (
      <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        <div className="flex justify-between items-center">
            <h1 className="text-2xl sm:text-3xl font-bold">Invoices</h1>
        </div>
        <Card className="w-full">
            <CardHeader>
                <CardTitle>No Active Organization</CardTitle>
                <CardDescription>You need to select an organization to manage its invoices.</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="text-center py-10">
                    <p className="text-muted-foreground mb-2">Please select an active organization from the header or go to the organizations page to select/create one.</p>
                    <Button asChild className="mt-4">
                        <Link to="/organizations">Manage Organizations</Link>
                    </Button>
                </div>
            </CardContent>
        </Card>
      </div>
    );
  }
  
  if (isLoading && invoices.length === 0 && !error) {
     return (
        <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
             <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
                <h1 className="text-2xl sm:text-3xl font-bold">Invoices for {activeOrganization.name}</h1>
                <Button onClick={handleCreateInvoice} disabled>
                    <PlusCircle className="mr-2 h-4 w-4" /> Create Invoice
                </Button>
            </div>
            <Card className="w-full">
                <CardHeader/>
                <CardContent>
                    <div className="text-center py-10">Loading invoices...</div>
                </CardContent>
            </Card>
        </div>
     );
  }

  return (
    <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-2xl sm:text-3xl font-bold">Invoices for {activeOrganization.name}</h1>
        <Button onClick={handleCreateInvoice}>
          <PlusCircle className="mr-2 h-4 w-4" /> Create Invoice
        </Button>
      </div>

      {error && invoices.length === 0 && (
         <Card className="w-full">
            <CardHeader><CardTitle>Error</CardTitle></CardHeader>
            <CardContent className="py-10">
                <p className="text-center text-destructive">{error}</p>
            </CardContent>
         </Card>
      )}
      
      {error && invoices.length > 0 && ( // Display error as a notice if data is already loaded
        <p className="mb-4 text-center text-sm text-destructive bg-destructive/10 p-3 rounded-md">{error}</p>
      )}


      <Card className="w-full">
        <CardHeader>
            {/* <CardTitle>Invoice List</CardTitle> */}
            {/* Add filter section here later if needed */}
        </CardHeader>
        <CardContent className={(invoices.length === 0 && !isLoading && !error) ? "pt-6" : "p-0 sm:p-6"}> {/* Adjust padding */}
          {!isLoading && invoices.length === 0 && !error ? (
            <div className="text-center py-10 border-2 border-dashed border-muted rounded-lg m-4 sm:m-0">
                <FileTextIcon className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-2 text-xl font-semibold">No Invoices Yet</h3>
                <p className="mt-1 text-sm text-muted-foreground">No invoices found for {activeOrganization.name}.</p>
                <div className="mt-6">
                    <Button onClick={handleCreateInvoice}>
                        <PlusCircle className="mr-2 h-4 w-4" /> Create First Invoice
                    </Button>
                </div>
            </div>
          ) : (
            !error && invoices.length > 0 && ( // Only show table if no error and invoices exist
                <div className="rounded-md border overflow-x-auto">
                    <Table>
                    <TableHeader>
                        <TableRow>
                        <TableHead>Number</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead className="hidden sm:table-cell">Customer</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Total</TableHead>
                        <TableHead className="text-right pr-2 sm:pr-4">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {invoices.map((inv) => (
                        <TableRow key={inv.id}>
                            <TableCell className="font-medium">{inv.invoice_number}</TableCell>
                            <TableCell>{inv.invoice_date ? format(parseISO(inv.invoice_date as unknown as string), "MMM dd, yyyy") : 'N/A'}</TableCell>
                            <TableCell className="hidden sm:table-cell">{inv.customer_company_name || 'N/A'}</TableCell>
                            <TableCell><Badge variant="outline" className="whitespace-nowrap">{inv.invoice_type}</Badge></TableCell>
                            <TableCell><Badge variant={getStatusBadgeVariant(inv.status)} className="whitespace-nowrap">{inv.status}</Badge></TableCell>
                            <TableCell className="text-right font-semibold whitespace-nowrap">{inv.currency} {inv.total_amount.toFixed(2)}</TableCell>
                            <TableCell className="text-right">
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild><Button variant="ghost" className="h-8 w-8 p-0"><MoreHorizontal className="h-4 w-4" /></Button></DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                {/* <DropdownMenuItem onClick={() => navigate(`/invoices/view/${inv.id}`)} className="cursor-pointer"><EyeIcon className="mr-2 h-4 w-4" />View</DropdownMenuItem> */}
                                <DropdownMenuItem onClick={() => handleDownloadPdf(inv.id, inv.invoice_number)} className="cursor-pointer"><DownloadIcon className="mr-2 h-4 w-4" />Download PDF</DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleEditInvoice(inv.id)} className="cursor-pointer"><Edit2Icon className="mr-2 h-4 w-4" />Edit</DropdownMenuItem>
                                {inv.invoice_type === InvoiceTypeEnum.PRO_FORMA && inv.status !== InvoiceStatusEnum.CANCELLED && (
                                    <DropdownMenuItem onClick={() => handleTransformToCommercial(inv.id)} className="cursor-pointer"><RefreshCwIcon className="mr-2 h-4 w-4" />To Commercial</DropdownMenuItem>
                                )}
                                {/* <DropdownMenuItem onClick={() => alert('Send Invoice clicked')} className="cursor-pointer"><SendIcon className="mr-2 h-4 w-4" />Send Invoice</DropdownMenuItem> */}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem 
                                    className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer"
                                    onClick={() => {
                                        console.log("DEBUG: Delete DropdownMenuItem clicked for:", inv); // Log click on item itself
                                        openDeleteConfirmDialog(inv);
                                    }}
                                >
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
            )
          )}
          {isLoading && (invoices.length > 0 || error) && (
            <div className="text-center py-4 text-sm text-muted-foreground">Refreshing invoices...</div>
          )}
        </CardContent>
      </Card>
      
      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete invoice "
              <strong>{invoiceToDelete?.invoice_number || ''}</strong>".
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { console.log("DEBUG: Delete Cancelled"); setInvoiceToDelete(null); setIsDeleteDialogOpen(false); }}>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={() => { console.log("DEBUG: Confirm Delete button in Dialog clicked"); handleConfirmDelete(); }}
              disabled={isDeleting}
              className="bg-destructive hover:bg-destructive/90 text-destructive-foreground"
            >
              {isDeleting ? "Deleting..." : "Yes, delete invoice"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
export default InvoicesPage;