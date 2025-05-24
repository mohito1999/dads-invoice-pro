// src/pages/InvoicesPage.tsx
import { useEffect, useState, useMemo } from 'react';
import apiClient from '@/services/apiClient';
import { InvoiceSummary, InvoiceStatusEnum, InvoiceTypeEnum, CustomerSummary, OrganizationSummary } from '@/types';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { 
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { MoreHorizontal, PlusCircle, Edit2Icon, Trash2Icon, FileTextIcon, DownloadIcon, RefreshCwIcon, EyeIcon, SendIcon, FilterIcon, PackageIcon } from "lucide-react";
import { useOrg } from '@/contexts/OrgContext';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from "@/components/ui/badge";
import { format, parseISO } from 'date-fns';


// Helper to get badge variant based on status
const getStatusBadgeVariant = (status: InvoiceStatusEnum): "default" | "secondary" | "destructive" | "outline" => {
  switch (status) {
    case InvoiceStatusEnum.PAID: return "default";
    case InvoiceStatusEnum.PARTIALLY_PAID: return "secondary";
    case InvoiceStatusEnum.OVERDUE: return "destructive";
    case InvoiceStatusEnum.UNPAID: return "outline";
    case InvoiceStatusEnum.DRAFT: return "secondary";
    case InvoiceStatusEnum.CANCELLED: return "destructive";
    default: return "outline";
  }
};


const InvoicesPage = () => {
  const { activeOrganization, isLoadingOrgs: isLoadingActiveOrg } = useOrg();
  const navigate = useNavigate();
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [invoiceToDelete, setInvoiceToDelete] = useState<InvoiceSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fetchInvoices = async (orgId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ organization_id: orgId, skip: "0", limit: "100" });
      const response = await apiClient.get<InvoiceSummary[]>(`/invoices/?${params.toString()}`);
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

  const handleDownloadDocumentPdf = async (invoiceId: string, invoiceNumber: string, docType: 'invoice' | 'packing-list') => {
    const endpoint = docType === 'packing-list' 
      ? `/invoices/${invoiceId}/packing-list-pdf` 
      : `/invoices/${invoiceId}/pdf`;
    const prefix = docType === 'packing-list' ? 'PackingList' : 'Invoice';
    try {
        setIsLoading(true); 
        const response = await apiClient.get(endpoint, { responseType: 'blob' });
        const blob = new Blob([response.data], { type: 'application/pdf' });
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = `${prefix}-${invoiceNumber.replace(/[\/\s]/g, '_')}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(link.href);
    } catch (err: any) {
        console.error(`Failed to download ${prefix} PDF:`, err);
        alert(err.response?.data?.detail || `Failed to download ${prefix} PDF.`);
    } finally {
        setIsLoading(false);
    }
  };
  
  const handleTransformToCommercial = async (invoiceId: string) => {
     if(!confirm("This will create a new Commercial Invoice based on this Pro Forma. Continue?")) return;
     try {
         setIsLoading(true);
         const response = await apiClient.post(`/invoices/${invoiceId}/transform-to-commercial`);
         alert(`Successfully transformed to Commercial Invoice: ${response.data.invoice_number}`);
         if(activeOrganization?.id) fetchInvoices(activeOrganization.id);
     } catch (err: any) {
         alert(err.response?.data?.detail || "Failed to transform invoice.");
     } finally {
         setIsLoading(false);
     }
  };

  const handleGeneratePackingList = async (commercialInvoiceId: string, commercialInvoiceNumber: string) => {
    if (!confirm(`Generate a Packing List based on Commercial Invoice ${commercialInvoiceNumber}?`)) return;
    
    const newPackingListNumber = prompt("Optional: Enter a specific number for the new Packing List (or leave blank for default):");
  
    try {
      setIsLoading(true);
      const response = await apiClient.post(`/invoices/${commercialInvoiceId}/generate-packing-list`, null, {
          params: newPackingListNumber ? { new_packing_list_number: newPackingListNumber } : {}
      });
      alert(`Successfully generated Packing List: ${response.data.invoice_number}`);
      if (activeOrganization?.id) fetchInvoices(activeOrganization.id);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to generate Packing List.");
      console.error("Packing List generation error:", err);
    } finally {
        setIsLoading(false);
    }
  };

  const openDeleteConfirmDialog = (invToDelete: InvoiceSummary) => {
    // console.log("DEBUG: openDeleteConfirmDialog called for invoice:", invToDelete); // Kept from previous debug
    setInvoiceToDelete(invToDelete);
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    // console.log("DEBUG: handleConfirmDelete attempting for:", invoiceToDelete); // Kept from previous debug
    if (!invoiceToDelete) {
    //   console.log("DEBUG: No invoiceToDelete set, exiting handleConfirmDelete."); // Kept from previous debug
      return;
    }
    
    // console.log(`DEBUG: Would call API: DELETE /invoices/${invoiceToDelete.id}`); // Kept from previous debug
    
    setIsDeleting(true);
    setError(null);
    try {
      await apiClient.delete(`/invoices/${invoiceToDelete.id}`);
      setInvoices(prevInvoices => prevInvoices.filter(i => i.id !== invoiceToDelete.id));
      alert(`Invoice "${invoiceToDelete.invoice_number}" deleted successfully.`);
    } catch (err: any) {
      console.error("Failed to delete invoice:", err);
      const errorMsg = err.response?.data?.detail || "Failed to delete invoice.";
      setError(errorMsg);
      alert(errorMsg);
    } finally {
      setIsDeleting(false);
      setIsDeleteDialogOpen(false);
      setInvoiceToDelete(null);
    }
  };

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
      
      {error && invoices.length > 0 && (
        <p className="mb-4 text-center text-sm text-destructive bg-destructive/10 p-3 rounded-md">{error}</p>
      )}

      <Card className="w-full">
        <CardHeader>
        </CardHeader>
        <CardContent className={(invoices.length === 0 && !isLoading && !error) ? "pt-6" : "p-0 sm:p-6"}>
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
            !error && invoices.length > 0 && (
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
                        {invoices.map((inv) => {
                            // --- ADDED DEBUG LOG FOR INVOICE TYPE ---
                            if (inv.invoice_number) { // Log only if invoice_number exists to avoid too much noise during render
                                console.log(
                                    "Invoice type from backend for inv", 
                                    inv.invoice_number, 
                                    ": '", inv.invoice_type, "' (type:", typeof inv.invoice_type, ")",
                                    "TS Enum PRO_FORMA is:", InvoiceTypeEnum.PRO_FORMA, 
                                    "TS Enum COMMERCIAL is:", InvoiceTypeEnum.COMMERCIAL,
                                    "TS Enum PACKING_LIST is:", InvoiceTypeEnum.PACKING_LIST 
                                );
                            }
                            // --- END DEBUG LOG ---
                            return (
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
                                        <DropdownMenuItem onClick={() => handleDownloadDocumentPdf(inv.id, inv.invoice_number, 'invoice')} className="cursor-pointer"><DownloadIcon className="mr-2 h-4 w-4" />Download Invoice PDF</DropdownMenuItem>
                                        
                                        {/* Conditional rendering for Packing List PDF Download */}
                                        {inv.invoice_type === InvoiceTypeEnum.PACKING_LIST && (
                                            <DropdownMenuItem 
                                                onClick={() => handleDownloadDocumentPdf(inv.id, inv.invoice_number, 'packing-list')} 
                                                className="cursor-pointer"
                                            >
                                                <DownloadIcon className="mr-2 h-4 w-4" />
                                                Download Packing List PDF
                                            </DropdownMenuItem>
                                        )}

                                        <DropdownMenuItem onClick={() => handleEditInvoice(inv.id)} className="cursor-pointer"><Edit2Icon className="mr-2 h-4 w-4" />Edit</DropdownMenuItem>
                                        
                                        {/* Conditional rendering for "To Commercial" */}
                                        {inv.invoice_type === InvoiceTypeEnum.PRO_FORMA && inv.status !== InvoiceStatusEnum.CANCELLED && (
                                            <DropdownMenuItem onClick={() => handleTransformToCommercial(inv.id)} className="cursor-pointer"><RefreshCwIcon className="mr-2 h-4 w-4" />To Commercial</DropdownMenuItem>
                                        )}

                                        {/* Conditional rendering for "Generate Packing List" */}
                                        {inv.invoice_type === InvoiceTypeEnum.COMMERCIAL && inv.status !== InvoiceStatusEnum.CANCELLED && (
                                            <DropdownMenuItem 
                                                onClick={() => handleGeneratePackingList(inv.id, inv.invoice_number)} 
                                                className="cursor-pointer"
                                            >
                                                <PackageIcon className="mr-2 h-4 w-4" />
                                                Generate Packing List
                                            </DropdownMenuItem>
                                        )}

                                        <DropdownMenuSeparator />
                                        <DropdownMenuItem 
                                            className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer"
                                            onClick={() => {
                                                // console.log("DEBUG: Delete DropdownMenuItem clicked for:", inv); // Kept from previous debug
                                                openDeleteConfirmDialog(inv);
                                            }}
                                        >
                                            <Trash2Icon className="mr-2 h-4 w-4" />Delete
                                        </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                    </TableCell>
                                </TableRow>
                            );
                        })}
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
            <AlertDialogCancel onClick={() => { /* console.log("DEBUG: Delete Cancelled"); */ setInvoiceToDelete(null); setIsDeleteDialogOpen(false); }}>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={() => { /* console.log("DEBUG: Confirm Delete button in Dialog clicked"); */ handleConfirmDelete(); }}
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