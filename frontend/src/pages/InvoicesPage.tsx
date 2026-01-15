// src/pages/InvoicesPage.tsx
import { useEffect, useState, useMemo, useCallback } from 'react';
import apiClient from '@/services/apiClient';
import { InvoiceSummary, InvoiceStatusEnum, InvoiceTypeEnum, CustomerSummary, OrganizationSummary, Invoice } from '@/types';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label"; // For the new Dialog
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter // Added DialogFooter
} from "@/components/ui/dialog";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle
} from "@/components/ui/alert-dialog";
import {
  MoreHorizontal, PlusCircle, Edit2Icon, Trash2Icon, FileTextIcon,
  DownloadIcon, RefreshCwIcon, EyeIcon, SendIcon, FilterIcon, PackageIcon, SearchIcon, XIcon, DollarSignIcon
} from "lucide-react";
import { useOrg } from '@/contexts/OrgContext';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from "@/components/ui/badge";
import { DatePicker } from "@/components/ui/date-picker";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { format, parseISO } from 'date-fns';
import { toast } from 'sonner';
import RecordPaymentForm from '@/components/invoices/RecordPaymentForm'; // Assuming this exists

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

const formatEnumValueForDisplay = (enumValue: string): string => {
  if (!enumValue) return '';
  return enumValue.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

const ALL_STATUSES_PLACEHOLDER = "---ALL_STATUSES---";
const ALL_CUSTOMERS_FILTER_PLACEHOLDER = "---ALL_CUSTOMERS_FILTER---";

const InvoicesPage = () => {
  const { activeOrganization, isLoadingOrgs: isLoadingActiveOrg } = useOrg();
  const navigate = useNavigate();

  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false); // General loading for list & actions
  const [error, setError] = useState<string | null>(null);

  // Filter State
  const [customersForFilter, setCustomersForFilter] = useState<CustomerSummary[]>([]);
  const [selectedStatus, setSelectedStatus] = useState<string>(ALL_STATUSES_PLACEHOLDER);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>(ALL_CUSTOMERS_FILTER_PLACEHOLDER);
  const [dateFrom, setDateFrom] = useState<Date | undefined>(undefined);
  const [dateTo, setDateTo] = useState<Date | undefined>(undefined);
  const [invoiceNumberSearch, setInvoiceNumberSearch] = useState<string>("");

  // Delete Confirmation state
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [invoiceToDelete, setInvoiceToDelete] = useState<InvoiceSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Payment Modal state
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [invoiceForPayment, setInvoiceForPayment] = useState<InvoiceSummary | null>(null);

  // --- State for "Transform to Commercial" AlertDialog ---
  const [isTransformConfirmOpen, setIsTransformConfirmOpen] = useState(false);
  const [invoiceToTransform, setInvoiceToTransform] = useState<InvoiceSummary | null>(null);

  // --- State for "Generate Packing List" Dialogs ---
  const [isPackingListNumberDialogOpen, setIsPackingListNumberDialogOpen] = useState(false); // For number input
  const [isPackingListConfirmOpen, setIsPackingListConfirmOpen] = useState(false);      // For final confirmation
  const [invoiceForPackingList, setInvoiceForPackingList] = useState<InvoiceSummary | null>(null);
  const [newPackingListNumberInput, setNewPackingListNumberInput] = useState('');


  const fetchInvoices = useCallback(async () => {
    if (!activeOrganization?.id) {
      setInvoices([]); setIsLoading(false); return;
    }
    setIsLoading(true); setError(null);
    try {
      const params = new URLSearchParams({
        organization_id: activeOrganization.id, skip: "0", limit: "100"
      });
      if (selectedStatus && selectedStatus !== ALL_STATUSES_PLACEHOLDER) params.append('status', selectedStatus);
      if (selectedCustomerId && selectedCustomerId !== ALL_CUSTOMERS_FILTER_PLACEHOLDER) params.append('customer_id', selectedCustomerId);
      if (dateFrom) params.append('date_from', format(dateFrom, 'yyyy-MM-dd'));
      if (dateTo) params.append('date_to', format(dateTo, 'yyyy-MM-dd'));
      if (invoiceNumberSearch.trim() !== "") params.append('invoice_number_search', invoiceNumberSearch.trim());

      const response = await apiClient.get<InvoiceSummary[]>(`/invoices/?${params.toString()}`);
      setInvoices(response.data);
    } catch (err: any) {
      console.error("Failed to fetch invoices:", err);
      setError(err.response?.data?.detail || 'Failed to load invoices.');
      setInvoices([]);
    } finally {
      setIsLoading(false);
    }
  }, [activeOrganization, selectedStatus, selectedCustomerId, dateFrom, dateTo, invoiceNumberSearch]);

  useEffect(() => {
    if (activeOrganization?.id) {
      apiClient.get<CustomerSummary[]>(`/customers/?organization_id=${activeOrganization.id}&limit=1000`)
        .then(res => setCustomersForFilter(res.data))
        .catch(err => { console.error("Failed to fetch customers for filter:", err); setCustomersForFilter([]); });
    } else if (!isLoadingActiveOrg) {
      setCustomersForFilter([]);
    }
  }, [activeOrganization, isLoadingActiveOrg]);

  useEffect(() => {
    if (activeOrganization?.id && !isLoadingActiveOrg) {
      fetchInvoices();
    } else if (!isLoadingActiveOrg && !activeOrganization) {
      setInvoices([]);
    }
  }, [activeOrganization, isLoadingActiveOrg, fetchInvoices]);

  const handleCreateInvoice = () => {
    if (activeOrganization) navigate(`/invoices/new?orgId=${activeOrganization.id}`);
    else toast.error("Please select an active organization first.");
  };
  const handleEditInvoice = (invoiceId: string) => navigate(`/invoices/edit/${invoiceId}`);

  const handleDownloadDocumentPdf = async (invoiceId: string, invoiceNumber: string, docType: 'invoice' | 'packing-list') => { /* ... (same as before) ... */
    const endpoint = docType === 'packing-list'
      ? `/invoices/${invoiceId}/packing-list-pdf`
      : `/invoices/${invoiceId}/pdf`;
    const prefix = docType === 'packing-list' ? 'PackingList' : 'Invoice';
    const GIsLoading = toast.loading(`Downloading ${prefix} PDF...`);
    try {
      const response = await apiClient.get(endpoint, { responseType: 'blob' });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = `${prefix}-${invoiceNumber.replace(/[\/\s]/g, '_')}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(link.href);
      toast.success(`${prefix} PDF downloaded.`, { id: GIsLoading });
    } catch (err: any) {
      console.error(`Failed to download ${prefix} PDF:`, err);
      toast.error(err.response?.data?.detail || `Failed to download ${prefix} PDF.`, { id: GIsLoading });
    }
  };

  // --- "Transform to Commercial" Handlers ---
  const openTransformConfirmDialog = (inv: InvoiceSummary) => {
    setInvoiceToTransform(inv);
    setIsTransformConfirmOpen(true);
  };

  const proceedWithTransformToCommercial = async () => {
    if (!invoiceToTransform) return;
    const GIsLoading = toast.loading("Transforming to Commercial Invoice...");
    try {
      const response = await apiClient.post(`/invoices/${invoiceToTransform.id}/transform-to-commercial`);
      toast.success(`Successfully transformed "${invoiceToTransform.invoice_number}" to Commercial Invoice: ${response.data.invoice_number}`, { id: GIsLoading });
      if (activeOrganization?.id) fetchInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to transform invoice.", { id: GIsLoading });
      console.error("Transform invoice error:", err);
    } finally {
      setIsTransformConfirmOpen(false);
      setInvoiceToTransform(null);
    }
  };
  // --- End "Transform to Commercial" Handlers ---

  // --- "Generate Packing List" Handlers ---
  const openPackingListNumberDialog = (inv: InvoiceSummary) => {
    setInvoiceForPackingList(inv);
    setNewPackingListNumberInput('');
    setIsPackingListNumberDialogOpen(true);
  };

  const proceedToGeneratePackingListConfirm = () => {
    setIsPackingListNumberDialogOpen(false);
    setIsPackingListConfirmOpen(true);
  };

  const executePackingListGeneration = async () => {
    if (!invoiceForPackingList) return;
    const GIsLoading = toast.loading("Generating Packing List...");
    try {
      const response = await apiClient.post(
        `/invoices/${invoiceForPackingList.id}/generate-packing-list`,
        null,
        {
          params: newPackingListNumberInput.trim() ? { new_invoice_number: newPackingListNumberInput.trim() } : {}
        }
      );
      toast.success(`Successfully generated Packing List: ${response.data.invoice_number}`, { id: GIsLoading });
      if (activeOrganization?.id) fetchInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to generate Packing List.", { id: GIsLoading });
      console.error("Packing List generation error:", err);
    } finally {
      setIsPackingListConfirmOpen(false);
      setInvoiceForPackingList(null);
      setNewPackingListNumberInput('');
    }
  };
  // --- End "Generate Packing List" Handlers ---

  const openDeleteConfirmDialog = (invToDelete: InvoiceSummary) => {
    setInvoiceToDelete(invToDelete); setIsDeleteDialogOpen(true);
  };
  const handleConfirmDelete = async () => {
    if (!invoiceToDelete) return;
    setIsDeleting(true); setError(null);
    const GIsLoading = toast.loading(`Deleting invoice ${invoiceToDelete.invoice_number}...`)
    try {
      await apiClient.delete(`/invoices/${invoiceToDelete.id}`);
      toast.success(`Invoice "${invoiceToDelete.invoice_number}" deleted successfully.`, { id: GIsLoading });
      fetchInvoices();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Failed to delete invoice.";
      setError(errorMsg);
      toast.error(errorMsg, { id: GIsLoading });
    }
    finally {
      setIsDeleting(false); setIsDeleteDialogOpen(false); setInvoiceToDelete(null);
    }
  };

  const clearFilters = () => {
    setSelectedStatus(ALL_STATUSES_PLACEHOLDER);
    setSelectedCustomerId(ALL_CUSTOMERS_FILTER_PLACEHOLDER);
    setDateFrom(undefined);
    setDateTo(undefined);
    setInvoiceNumberSearch("");
  };

  const handleOpenPaymentModal = (invoice: InvoiceSummary) => {
    setInvoiceForPayment(invoice);
    setIsPaymentModalOpen(true);
  };

  const handlePaymentRecorded = (updatedInvoice: Invoice) => {
    fetchInvoices();
    setIsPaymentModalOpen(false);
    setInvoiceForPayment(null);
    toast.success(`Payment recorded for invoice ${updatedInvoice.invoice_number}. Status: ${updatedInvoice.status}`);
  };

  if (isLoadingActiveOrg) return <div className="container mx-auto px-4 py-10 text-center">Loading organization context...</div>;
  if (!activeOrganization) return ( /* ... No Active Organization Card ... */
    <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      <div className="flex justify-between items-center"> <h1 className="text-2xl sm:text-3xl font-bold">Invoices</h1> </div>
      <Card className="w-full">
        <CardHeader><CardTitle>No Active Organization</CardTitle><CardDescription>You need to select an organization to manage its invoices.</CardDescription></CardHeader>
        <CardContent><div className="text-center py-10"><p className="text-muted-foreground mb-2">Please select an active organization from the header or go to the organizations page to select/create one.</p><Button asChild className="mt-4"><Link to="/organizations">Manage Organizations</Link></Button></div></CardContent>
      </Card>
    </div>
  );

  return (
    <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-2xl sm:text-3xl font-bold">Invoices for {activeOrganization.name}</h1>
        <Button onClick={handleCreateInvoice}>
          <PlusCircle className="mr-2 h-4 w-4" /> Create Invoice
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Refine the list of invoices below.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-5 gap-4 items-end">
            <div className="lg:col-span-1 xl:col-span-1">
              <Label htmlFor="invoiceNumberSearch">Search #</Label>
              <div className="relative mt-1">
                <SearchIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input id="invoiceNumberSearch" placeholder="e.g., INV-001" value={invoiceNumberSearch} onChange={(e) => setInvoiceNumberSearch(e.target.value)} className="pl-9" />
                {invoiceNumberSearch && (<Button variant="ghost" size="icon" className="absolute right-0 top-1/2 -translate-y-1/2 h-8 w-8" onClick={() => setInvoiceNumberSearch('')}><XIcon className="h-4 w-4" /></Button>)}
              </div>
            </div>
            <div>
              <Label htmlFor="customerFilter">Customer</Label>
              <Select value={selectedCustomerId} onValueChange={setSelectedCustomerId}>
                <SelectTrigger id="customerFilter" className="mt-1"><SelectValue placeholder="All Customers" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_CUSTOMERS_FILTER_PLACEHOLDER}>All Customers</SelectItem>
                  {customersForFilter.map(c => (<SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="statusFilter">Status</Label>
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger id="statusFilter" className="mt-1"><SelectValue placeholder="All Statuses" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL_STATUSES_PLACEHOLDER}>All Statuses</SelectItem>
                  {Object.values(InvoiceStatusEnum).map(s => (<SelectItem key={s} value={s.valueOf()}>{formatEnumValueForDisplay(s.valueOf())}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div><Label htmlFor="dateFromFilter">Date From</Label><DatePicker date={dateFrom} onDateChange={setDateFrom} className="mt-1" placeholder="Start Date" /></div>
            <div><Label htmlFor="dateToFilter">Date To</Label><DatePicker date={dateTo} onDateChange={setDateTo} className="mt-1" placeholder="End Date" /></div>
          </div>
          <div className="flex justify-end mt-4"><Button onClick={clearFilters} variant="ghost" size="sm"><XIcon className="mr-2 h-4 w-4" /> Clear Filters</Button></div>
        </CardContent>
      </Card>

      {isLoading && (<Card className="w-full"><CardContent className="py-10 text-center">Loading invoices...</CardContent></Card>)}
      {!isLoading && error && (<Card className="w-full"><CardHeader><CardTitle>Error</CardTitle></CardHeader><CardContent className="py-10"><p className="text-center text-destructive">{error}</p></CardContent></Card>)}
      {!isLoading && !error && invoices.length === 0 && (
        <Card className="w-full">
          <CardHeader><CardTitle>No Invoices Found</CardTitle><CardDescription>{invoiceNumberSearch || selectedStatus !== ALL_STATUSES_PLACEHOLDER || selectedCustomerId !== ALL_CUSTOMERS_FILTER_PLACEHOLDER || dateFrom || dateTo ? "No invoices match your current filter criteria." : `No invoices found for ${activeOrganization.name}.`}</CardDescription></CardHeader>
          <CardContent className="py-10 text-center"><FileTextIcon className="mx-auto h-12 w-12 text-muted-foreground mb-4" /><p className="text-muted-foreground mb-4">{invoiceNumberSearch || selectedStatus !== ALL_STATUSES_PLACEHOLDER || selectedCustomerId !== ALL_CUSTOMERS_FILTER_PLACEHOLDER || dateFrom || dateTo ? "Try adjusting your filters or create a new invoice." : "Get started by creating your first invoice for this organization."}</p><Button onClick={handleCreateInvoice}><PlusCircle className="mr-2 h-4 w-4" /> Create Invoice</Button></CardContent>
        </Card>
      )}

      {!isLoading && !error && invoices.length > 0 && (
        <Card className="w-full">
          <CardHeader>{/* Optional Title */}</CardHeader>
          <CardContent className="p-0 sm:p-6">
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader><TableRow><TableHead>Number</TableHead><TableHead>Date</TableHead><TableHead className="hidden sm:table-cell">Customer</TableHead><TableHead>Type</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Total</TableHead><TableHead className="text-right pr-2 sm:pr-4">Actions</TableHead></TableRow></TableHeader>
                <TableBody>
                  {invoices.map((inv) => (
                    <TableRow key={inv.id}>
                      <TableCell className="font-medium">{inv.invoice_number}</TableCell>
                      <TableCell>{inv.invoice_date ? format(parseISO(inv.invoice_date as unknown as string), "MMM dd, yyyy") : 'N/A'}</TableCell>
                      <TableCell className="hidden sm:table-cell">{inv.customer_company_name || 'N/A'}</TableCell>
                      <TableCell><Badge variant="outline" className="whitespace-nowrap">{formatEnumValueForDisplay(inv.invoice_type.valueOf())}</Badge></TableCell>
                      <TableCell><Badge variant={getStatusBadgeVariant(inv.status)} className="whitespace-nowrap">{formatEnumValueForDisplay(inv.status.valueOf())}</Badge></TableCell>
                      <TableCell className="text-right font-semibold whitespace-nowrap">{inv.currency} {inv.total_amount.toFixed(2)}</TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild><Button variant="ghost" className="h-8 w-8 p-0"><MoreHorizontal className="h-4 w-4" /></Button></DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuItem onClick={() => handleDownloadDocumentPdf(inv.id, inv.invoice_number, 'invoice')} className="cursor-pointer"><DownloadIcon className="mr-2 h-4 w-4" />Download Invoice PDF</DropdownMenuItem>
                            {inv.invoice_type.valueOf() === InvoiceTypeEnum.PACKING_LIST.valueOf() && (<DropdownMenuItem onClick={() => handleDownloadDocumentPdf(inv.id, inv.invoice_number, 'packing-list')} className="cursor-pointer"><DownloadIcon className="mr-2 h-4 w-4" /> Download Packing List PDF</DropdownMenuItem>)}
                            <DropdownMenuItem onClick={() => handleEditInvoice(inv.id)} className="cursor-pointer"><Edit2Icon className="mr-2 h-4 w-4" />Edit</DropdownMenuItem>
                            {inv.invoice_type.valueOf() === InvoiceTypeEnum.PRO_FORMA.valueOf() && inv.status !== InvoiceStatusEnum.CANCELLED && (<DropdownMenuItem onClick={() => openTransformConfirmDialog(inv)} className="cursor-pointer"><RefreshCwIcon className="mr-2 h-4 w-4" />To Commercial</DropdownMenuItem>)}
                            {inv.invoice_type.valueOf() === InvoiceTypeEnum.COMMERCIAL.valueOf() && inv.status !== InvoiceStatusEnum.CANCELLED && (<DropdownMenuItem onClick={() => openPackingListNumberDialog(inv)} className="cursor-pointer"><PackageIcon className="mr-2 h-4 w-4" /> Generate Packing List</DropdownMenuItem>)}
                            {(inv.status === InvoiceStatusEnum.UNPAID || inv.status === InvoiceStatusEnum.PARTIALLY_PAID || inv.status === InvoiceStatusEnum.OVERDUE) && (<DropdownMenuItem onClick={() => handleOpenPaymentModal(inv)} className="cursor-pointer"><DollarSignIcon className="mr-2 h-4 w-4" /> Record Payment</DropdownMenuItem>)}
                            <DropdownMenuSeparator />
                            <DropdownMenuItem className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer" onClick={() => openDeleteConfirmDialog(inv)}><Trash2Icon className="mr-2 h-4 w-4" />Delete</DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  )
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Payment Recording Dialog */}
      <Dialog open={isPaymentModalOpen} onOpenChange={setIsPaymentModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Record Payment for Invoice {invoiceForPayment?.invoice_number}</DialogTitle>
            <DialogDescription>Current Total: {invoiceForPayment?.currency} {invoiceForPayment?.total_amount.toFixed(2)}</DialogDescription>
          </DialogHeader>
          {invoiceForPayment && (<RecordPaymentForm invoice={invoiceForPayment} onSuccess={handlePaymentRecorded} onCancel={() => { setIsPaymentModalOpen(false); setInvoiceForPayment(null); }} />)}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation AlertDialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader><AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle><AlertDialogDescription>This action cannot be undone. This will permanently delete invoice "<strong>{invoiceToDelete?.invoice_number || ''}</strong>".</AlertDialogDescription></AlertDialogHeader>
          <AlertDialogFooter><AlertDialogCancel onClick={() => { setInvoiceToDelete(null); setIsDeleteDialogOpen(false); }}>Cancel</AlertDialogCancel><AlertDialogAction onClick={handleConfirmDelete} disabled={isDeleting} className="bg-destructive hover:bg-destructive/90 text-white">{isDeleting ? "Deleting..." : "Yes, delete invoice"}</AlertDialogAction></AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Transform to Commercial Confirmation Dialog */}
      {invoiceToTransform && (
        <AlertDialog open={isTransformConfirmOpen} onOpenChange={setIsTransformConfirmOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Confirm Transformation</AlertDialogTitle>
              <AlertDialogDescription>
                This will create a new Commercial Invoice based on Pro Forma Invoice "<strong>{invoiceToTransform.invoice_number}</strong>". The original Pro Forma will remain unchanged.
                <br /><br />
                Are you sure you want to continue?
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => { setInvoiceToTransform(null); setIsTransformConfirmOpen(false); }}>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={proceedWithTransformToCommercial} disabled={isLoading} >
                {isLoading ? "Transforming..." : "Yes, Transform"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      {/* Dialog to Enter Optional Packing List Number */}
      {invoiceForPackingList && (
        <Dialog open={isPackingListNumberDialogOpen} onOpenChange={(isOpen) => {
          setIsPackingListNumberDialogOpen(isOpen);
          if (!isOpen) setInvoiceForPackingList(null); // Clear context if dialog is closed
        }}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Generate Packing List for {invoiceForPackingList.invoice_number}</DialogTitle>
              <DialogDescription>Optionally enter a specific number for the new Packing List. Leave blank to use a default number generated by the system.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="packingListNumberInput" className="text-right col-span-1">PL Number</Label>
                <Input id="packingListNumberInput" value={newPackingListNumberInput} onChange={(e) => setNewPackingListNumberInput(e.target.value)} className="col-span-3" placeholder="e.g., PL-XYZ-001 (Optional)" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => { setIsPackingListNumberDialogOpen(false); setInvoiceForPackingList(null); }}>Cancel</Button>
              <Button onClick={proceedToGeneratePackingListConfirm}>Next: Confirm</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Final Confirmation AlertDialog for Generating Packing List */}
      {invoiceForPackingList && (
        <AlertDialog open={isPackingListConfirmOpen} onOpenChange={(isOpen) => {
          setIsPackingListConfirmOpen(isOpen);
          if (!isOpen) { // If closing confirm dialog, also clear related states
            setInvoiceForPackingList(null);
            setNewPackingListNumberInput('');
          }
        }}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Confirm Packing List Generation</AlertDialogTitle>
              <AlertDialogDescription>
                Generate a Packing List based on Commercial Invoice "<strong>{invoiceForPackingList.invoice_number}</strong>"?
                {newPackingListNumberInput.trim() && (<><br />It will be numbered: <strong>{newPackingListNumberInput.trim()}</strong>.</>)}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel onClick={() => { setIsPackingListConfirmOpen(false); setInvoiceForPackingList(null); setNewPackingListNumberInput(''); }}>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={executePackingListGeneration} disabled={isLoading}>
                {isLoading ? "Generating..." : "Yes, Generate"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
};
export default InvoicesPage;