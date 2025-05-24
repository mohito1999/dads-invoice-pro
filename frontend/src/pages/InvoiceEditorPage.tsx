// src/pages/InvoiceEditorPage.tsx
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { v4 as uuidv4 } from 'uuid';
import apiClient from '@/services/apiClient';
import { 
    Invoice, InvoiceCreate, InvoiceUpdate, InvoiceItemFormData, 
    InvoiceStatusEnum, InvoiceTypeEnum, PricePerTypeEnum,
    CustomerSummary, ItemSummary 
} from '@/types';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DatePicker } from "@/components/ui/date-picker";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Trash2Icon, PlusCircleIcon } from "lucide-react";
import { useOrg } from '@/contexts/OrgContext';
// import { useAuth } from '@/contexts/AuthContext';

// --- Define Placeholder Values ---
const CUSTOMER_PLACEHOLDER_VALUE = "---SELECT_CUSTOMER_PLACEHOLDER---";
const ITEM_PLACEHOLDER_VALUE = "---TYPE_MANUALLY_PLACEHOLDER---";

// --- Initial Currency Definition ---
const INITIAL_CURRENCY = 'USD';

// --- Helper function to create a default line item ---
const createDefaultLineItem = (currentInvoiceCurrency: string): InvoiceItemFormData => ({
    _temp_id: uuidv4(),
    item_id: undefined, 
    item_description: '',
    quantity_units: '1',
    unit_type: 'pieces',
    price: '0',
    price_per_type: PricePerTypeEnum.UNIT,
    currency: currentInvoiceCurrency,
});

// --- Calculation Functions ---
const round = (num: number, places: number = 2): number => {
    return parseFloat(num.toFixed(places));
};

const calculateLineItemTotal = (item: Partial<InvoiceItemFormData>): number => {
    const price = parseFloat(String(item.price)) || 0;
    let quantity = 0;

    if (item.price_per_type === PricePerTypeEnum.CARTON && (item.quantity_cartons || item.quantity_cartons === 0)) {
        quantity = parseFloat(String(item.quantity_cartons)) || 0;
    } else if (item.quantity_units || item.quantity_units === 0) {
        quantity = parseFloat(String(item.quantity_units)) || 0;
    }
    return round(price * quantity);
};

const calculateTotals = (
    lineItems: Partial<InvoiceItemFormData>[],
    taxPercent?: number | null,
    discountPercent?: number | null
): { subtotal: number; taxAmount: number; discountAmount: number; totalAmount: number } => {
    let subtotal = 0;
    lineItems.forEach(item => {
        subtotal += calculateLineItemTotal(item);
    });
    subtotal = round(subtotal);

    const taxAmount = taxPercent ? round(subtotal * (taxPercent / 100), 2) : 0;
    let discountAmount = discountPercent ? round(subtotal * (discountPercent / 100), 2) : 0;
    discountAmount = Math.min(discountAmount, subtotal);

    const totalAmount = round(subtotal + taxAmount - discountAmount, 2);
    return { subtotal, taxAmount, discountAmount, totalAmount };
};
// --- End Calculation Functions ---


const InvoiceEditorPage = () => {
  const { invoiceId } = useParams<{ invoiceId?: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { activeOrganization } = useOrg();

  const isEditMode = !!invoiceId;

  // Invoice Header State
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [invoiceDate, setInvoiceDate] = useState<Date | undefined>(new Date());
  const [dueDate, setDueDate] = useState<Date | undefined>();
  const [customerId, setCustomerId] = useState<string>(CUSTOMER_PLACEHOLDER_VALUE);
  const [invoiceType, setInvoiceType] = useState<InvoiceTypeEnum>(InvoiceTypeEnum.COMMERCIAL);
  const [status, setStatus] = useState<InvoiceStatusEnum>(InvoiceStatusEnum.DRAFT);
  
  const [currency, setCurrency] = useState(INITIAL_CURRENCY); 
  const [currencyInput, setCurrencyInput] = useState(INITIAL_CURRENCY); // For direct input typing

  const [taxPercentage, setTaxPercentage] = useState<string>('');
  const [discountPercentage, setDiscountPercentage] = useState<string>('');
  const [commentsNotes, setCommentsNotes] = useState('');
  
  const [lineItems, setLineItems] = useState<InvoiceItemFormData[]>(() => 
    !invoiceId ? [createDefaultLineItem(INITIAL_CURRENCY)] : []
  );

  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [items, setItems] = useState<ItemSummary[]>([]);

  const [isLoading, setIsLoading] = useState(false);
  const [isPageLoading, setIsPageLoading] = useState(isEditMode);
  const [error, setError] = useState<string | null>(null);

  const [calculatedSubtotal, setCalculatedSubtotal] = useState(0);
  const [calculatedTax, setCalculatedTax] = useState(0);
  const [calculatedDiscount, setCalculatedDiscount] = useState(0);
  const [calculatedTotal, setCalculatedTotal] = useState(0);

  // Fetch customers and items for dropdowns
  useEffect(() => {
    if (activeOrganization?.id) {
        if (!isEditMode) setIsPageLoading(true); 
        Promise.all([
            apiClient.get<CustomerSummary[]>(`/customers/?organization_id=${activeOrganization.id}`),
            apiClient.get<ItemSummary[]>(`/items/?organization_id=${activeOrganization.id}`)
        ]).then(([customersRes, itemsRes]) => {
            setCustomers(customersRes.data);
            setItems(itemsRes.data);
        }).catch(err => {
            console.error("Failed to fetch customers or items", err);
            setError("Failed to load dropdown data. Please ensure an organization is active and try again.");
        }).finally(() => {
            if (!isEditMode) setIsPageLoading(false);
        });
    }
  }, [activeOrganization, isEditMode]);

  // Fetch invoice data in edit mode OR setup for new invoice
  useEffect(() => {
    if (isEditMode && invoiceId) {
        setIsPageLoading(true);
        apiClient.get<Invoice>(`/invoices/${invoiceId}`)
            .then(response => {
                const inv = response.data;
                setInvoiceNumber(inv.invoice_number);
                setInvoiceDate(inv.invoice_date ? new Date(inv.invoice_date) : undefined);
                setDueDate(inv.due_date ? new Date(inv.due_date) : undefined);
                setCustomerId(inv.customer_id || CUSTOMER_PLACEHOLDER_VALUE);
                setInvoiceType(inv.invoice_type);
                setStatus(inv.status);
                setCurrency(inv.currency); 
                setCurrencyInput(inv.currency); // Sync currencyInput with fetched currency
                setTaxPercentage(inv.tax_percentage?.toString() || '');
                setDiscountPercentage(inv.discount_percentage?.toString() || '');
                setCommentsNotes(inv.comments_notes || '');
                setLineItems(inv.line_items.map(li => ({
                    id: li.id,
                    _temp_id: uuidv4(),
                    item_id: li.item_id || undefined,
                    item_description: li.item_description,
                    quantity_cartons: li.quantity_cartons?.toString() ?? '',
                    quantity_units: li.quantity_units?.toString() ?? '',
                    unit_type: li.unit_type || 'pieces',
                    price: li.price.toString(),
                    price_per_type: li.price_per_type,
                    currency: inv.currency, 
                    item_specific_comments: li.item_specific_comments || '',
                })));
            })
            .catch(err => {
                console.error("Failed to fetch invoice for editing:", err);
                setError("Failed to load invoice data.");
            })
            .finally(() => setIsPageLoading(false));
    } else { 
        setInvoiceNumber('');
        setInvoiceDate(new Date());
        setDueDate(undefined);
        setCustomerId(CUSTOMER_PLACEHOLDER_VALUE);
        setInvoiceType(InvoiceTypeEnum.COMMERCIAL);
        setStatus(InvoiceStatusEnum.DRAFT);
        setCurrency(INITIAL_CURRENCY); 
        setCurrencyInput(INITIAL_CURRENCY); // Reset currencyInput
        setTaxPercentage('');
        setDiscountPercentage('');
        setCommentsNotes('');
        // Initial line item is set by useState initializer if lineItems.length === 0 logic is removed from here
        // For safety and clarity, ensure it's correctly initialized or re-initialized:
        if (lineItems.length === 0 || !isEditMode) { // If create mode, ensure one item with current initial currency
             setLineItems([createDefaultLineItem(INITIAL_CURRENCY)]);
        }
    }
  }, [invoiceId, isEditMode]);


  // Recalculate totals
  useEffect(() => {
     const taxP = taxPercentage !== '' ? parseFloat(String(taxPercentage)) : null;
     const discP = discountPercentage !== '' ? parseFloat(String(discountPercentage)) : null;
     const totals = calculateTotals(lineItems, taxP, discP);
     setCalculatedSubtotal(totals.subtotal);
     setCalculatedTax(totals.taxAmount);
     setCalculatedDiscount(totals.discountAmount);
     setCalculatedTotal(totals.totalAmount);
  }, [lineItems, taxPercentage, discountPercentage]);

  const handleLineItemChange = (index: number, field: keyof InvoiceItemFormData, value: string | number | PricePerTypeEnum | undefined | null) => {
    const updatedLineItems = lineItems.map((item, idx) => {
        if (index === idx) {
            return { ...item, [field]: value };
        }
        return item;
    });
    setLineItems(updatedLineItems);
  };
  
  const handlePredefinedItemSelect = (index: number, selectedItemId: string) => {
    const updatedLineItems = [...lineItems];
    if (selectedItemId === ITEM_PLACEHOLDER_VALUE) {
        updatedLineItems[index] = {
            ...updatedLineItems[index],
            item_id: undefined, 
        };
    } else {
        const selectedItem = items.find(i => i.id === selectedItemId);
        if (selectedItem) {
            updatedLineItems[index] = {
                ...updatedLineItems[index],
                item_id: selectedItem.id,
                item_description: selectedItem.name,
                price: selectedItem.default_price?.toString() || '0',
                unit_type: selectedItem.default_unit || 'pieces',
                currency: currency, 
            };
        }
    }
    setLineItems(updatedLineItems);
  };

  const handleAddLineItem = useCallback(() => {
    setLineItems(prevItems => [...prevItems, createDefaultLineItem(currency)]);
  }, [currency]);

  const handleRemoveLineItem = (tempIdToRemove?: string, dbIdToRemove?: string) => {
    setLineItems(prevItems => 
        prevItems.filter(item => {
            if (tempIdToRemove) return item._temp_id !== tempIdToRemove;
            if (dbIdToRemove) return item.id !== dbIdToRemove;
            return true; 
        })
    );
  };

  const handleMainCurrencyChange = (inputValue: string) => {
    const upperValue = inputValue.toUpperCase();
    setCurrencyInput(upperValue); // Always update the input field's display

    if (upperValue.length === 3 && /^[A-Z]+$/.test(upperValue)) {
      setCurrency(upperValue); 
      setLineItems(prevLineItems => 
          prevLineItems.map(li => ({ ...li, currency: upperValue }))
      );
    } else if (upperValue.length > 3) {
        const validPart = upperValue.substring(0, 3);
        setCurrencyInput(validPart);
        if (/^[A-Z]+$/.test(validPart)) {
            setCurrency(validPart);
            setLineItems(prevLineItems => 
                prevLineItems.map(li => ({ ...li, currency: validPart }))
            );
        }
    } else if (inputValue === "") {
        setCurrencyInput("");
        // Optionally revert official currency to default or handle as error in submit
        // setCurrency(INITIAL_CURRENCY); 
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    let effectiveOrgId = activeOrganization?.id;
    if (!isEditMode && !effectiveOrgId) {
        const queryParams = new URLSearchParams(location.search);
        effectiveOrgId = queryParams.get('orgId') || undefined;
    }
    if (!isEditMode && !effectiveOrgId) {
        setError("Active organization is required to create an invoice.");
        return;
    }
    if (!customerId || customerId === CUSTOMER_PLACEHOLDER_VALUE) {
        setError("Customer is required. Please select a customer.");
        return;
    }
    if (lineItems.length === 0) {
        setError("Invoice must have at least one line item.");
        return;
    }
    for (const li of lineItems) {
        if (!li.item_description || !li.item_description.trim()) {
            setError("All line items must have a description."); return;
        }
        if (li.price === '' || li.price === undefined || isNaN(parseFloat(String(li.price))) || parseFloat(String(li.price)) < 0) {
            setError("All line items must have a valid, non-negative price."); return;
        }
    }
    if (!currency || currency.trim().length !== 3 || !/^[A-Z]+$/.test(currency)) { // Use validated 'currency' state
        setError("A valid 3-letter uppercase currency code is required for the invoice.");
        return;
    }

    setIsLoading(true);
    setError(null);

    const finalCustomerId = customerId === CUSTOMER_PLACEHOLDER_VALUE ? null : customerId;

    const finalLineItemsForAPI = lineItems.map(li => ({
        item_id: (li.item_id === ITEM_PLACEHOLDER_VALUE || !li.item_id) ? null : li.item_id,
        item_description: li.item_description,
        quantity_cartons: li.quantity_cartons ? parseFloat(String(li.quantity_cartons)) : null,
        quantity_units: li.quantity_units ? parseFloat(String(li.quantity_units)) : null,
        unit_type: li.unit_type,
        price: parseFloat(String(li.price)),
        price_per_type: li.price_per_type,
        currency: li.currency, 
        item_specific_comments: li.item_specific_comments || null,
    }));

    const payload: any = { 
        invoice_number: invoiceNumber,
        invoice_date: invoiceDate ? invoiceDate.toISOString().split('T')[0] : undefined,
        due_date: dueDate ? dueDate.toISOString().split('T')[0] : undefined,
        customer_id: finalCustomerId,
        invoice_type: invoiceType,
        status: status,
        currency: currency, // Use the validated main currency state
        tax_percentage: taxPercentage !== '' ? parseFloat(String(taxPercentage)) : null,
        discount_percentage: discountPercentage !== '' ? parseFloat(String(discountPercentage)) : null,
        comments_notes: commentsNotes || null,
        line_items: finalLineItemsForAPI,
    };
    if (!isEditMode && effectiveOrgId) {
        payload.organization_id = effectiveOrgId;
    }
    
    Object.keys(payload).forEach(key => payload[key as keyof typeof payload] === undefined && delete payload[key as keyof typeof payload]);

    try {
        if (isEditMode && invoiceId) {
            await apiClient.put<Invoice>(`/invoices/${invoiceId}`, payload as InvoiceUpdate);
        } else {
            await apiClient.post<Invoice>('/invoices/', payload as InvoiceCreate);
        }
        alert(`Invoice ${isEditMode ? 'updated' : 'created'} successfully!`);
        navigate('/invoices'); 
    } catch (err: any) {
        console.error(`Failed to ${isEditMode ? 'update' : 'create'} invoice:`, err);
        setError(err.response?.data?.detail || `An error occurred.`);
    } finally {
        setIsLoading(false);
    }
  };
  
  if (isPageLoading) return <div className="text-center py-10">Loading...</div>;
  
  return (
     <div className="space-y-6 mb-10">
         <h1 className="text-3xl font-bold">
             {isEditMode ? `Edit Invoice ${invoiceNumber || ''}` : `Create New Invoice for ${activeOrganization?.name || 'Selected Organization'}`}
         </h1>

         <form onSubmit={handleSubmit}>
             <Card>
                 <CardHeader><CardTitle>Invoice Details</CardTitle></CardHeader>
                 <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-6">
                     <div>
                         <Label htmlFor="invoice_number">Invoice Number</Label>
                         <Input id="invoice_number" value={invoiceNumber} onChange={e => setInvoiceNumber(e.target.value)} required className="mt-1" />
                     </div>
                     <div>
                        <Label htmlFor="customer_id">Customer</Label>
                        <Select 
                            value={customerId} 
                            onValueChange={(value) => {
                                setCustomerId(value); 
                            }}
                        >
                            <SelectTrigger className="mt-1">
                                <SelectValue placeholder="Select customer..." />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value={CUSTOMER_PLACEHOLDER_VALUE}>-- Select Customer --</SelectItem>
                                {customers.length === 0 && (
                                    <SelectItem value="no-actual-customers-placeholder" disabled>
                                        No customers available
                                    </SelectItem>
                                )}
                                {customers.map(c => <SelectItem key={c.id} value={c.id}>{c.company_name}</SelectItem>)}
                            </SelectContent>
                        </Select>
                     </div>
                     <div>
                         <Label htmlFor="invoice_date">Invoice Date</Label>
                         <DatePicker date={invoiceDate} onDateChange={setInvoiceDate} className="mt-1" />
                     </div>
                     <div>
                         <Label htmlFor="due_date">Due Date (Optional)</Label>
                         <DatePicker date={dueDate} onDateChange={setDueDate} className="mt-1" />
                     </div>
                     <div>
                         <Label htmlFor="invoice_type">Type</Label>
                         <Select value={invoiceType} onValueChange={(v) => setInvoiceType(v as InvoiceTypeEnum)}>
                             <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                             <SelectContent>
                                 {Object.values(InvoiceTypeEnum).map(type => <SelectItem key={type} value={type}>{type}</SelectItem>)}
                             </SelectContent>
                         </Select>
                     </div>
                     <div>
                         <Label htmlFor="status">Status</Label>
                         <Select value={status} onValueChange={(v) => setStatus(v as InvoiceStatusEnum)}>
                             <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                             <SelectContent>
                                 {Object.values(InvoiceStatusEnum).map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                             </SelectContent>
                         </Select>
                     </div>
                     <div>
                         <Label htmlFor="currency">Currency (e.g., USD)</Label>
                         <Input 
                            id="currency" 
                            value={currencyInput} 
                            onChange={e => handleMainCurrencyChange(e.target.value)} 
                            maxLength={3} // MaxLength is a good UX hint for user
                            required 
                            className="mt-1" 
                            placeholder="USD"
                            autoComplete="off" // Attempt to disable browser autocomplete
                         />
                     </div>
                 </CardContent>
             </Card>

             <Card>
                 <CardHeader><CardTitle>Line Items</CardTitle></CardHeader>
                 <CardContent>
                     <Table>
                         <TableHeader>
                             <TableRow>
                                 <TableHead className="min-w-[250px]">Item/Description</TableHead>
                                 <TableHead className="w-[100px]">Qty (Units)</TableHead>
                                 <TableHead className="w-[100px]">Unit Type</TableHead>
                                 <TableHead className="w-[100px]">Qty (Cartons)</TableHead>
                                 <TableHead className="w-[120px]">Price</TableHead>
                                 <TableHead className="w-[120px]">Price Per</TableHead>
                                 <TableHead className="w-[80px]">Currency</TableHead>
                                 <TableHead className="text-right w-[120px]">Line Total</TableHead>
                                 <TableHead className="w-[50px]">Del</TableHead>
                             </TableRow>
                         </TableHeader>
                         <TableBody>
                             {lineItems.map((item, index) => (
                             <TableRow key={item.id || item._temp_id}>
                                 <TableCell>
                                    <Select 
                                        onValueChange={(selectedItemId) => handlePredefinedItemSelect(index, selectedItemId)} 
                                        value={item.item_id || ITEM_PLACEHOLDER_VALUE}
                                    >
                                        <SelectTrigger><SelectValue placeholder="Select predefined item..." /></SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value={ITEM_PLACEHOLDER_VALUE}>-- Type Description Manually --</SelectItem> 
                                            {items.length === 0 && (
                                                <SelectItem value="no-actual-items-placeholder" disabled>
                                                    No predefined items
                                                </SelectItem>
                                            )}
                                            {items.map((i, itemIndex) => {
                                                const itemValue = (typeof i.id === 'string' && i.id.trim() !== "") ? i.id : `invalid-item-id-${itemIndex}-${uuidv4()}`;
                                                return (
                                                    <SelectItem key={itemValue} value={itemValue}> 
                                                        {i.name} ({i.default_price ? `${item.currency} ${i.default_price.toFixed(2)}` : 'N/A'})
                                                    </SelectItem>
                                                );
                                            })}
                                        </SelectContent>
                                    </Select>
                                    <Textarea 
                                        value={item.item_description} 
                                        onChange={e => handleLineItemChange(index, 'item_description', e.target.value)}
                                        placeholder="Or type item description"
                                        className="mt-1" rows={2} required
                                    />
                                 </TableCell>
                                 <TableCell><Input type="number" step="any" value={item.quantity_units || ''} onChange={e => handleLineItemChange(index, 'quantity_units', e.target.value)} placeholder="0" className="w-full" /></TableCell>
                                 <TableCell><Input value={item.unit_type || ''} onChange={e => handleLineItemChange(index, 'unit_type', e.target.value)} placeholder="pieces" className="w-full" /></TableCell>
                                 <TableCell><Input type="number" step="any" value={item.quantity_cartons || ''} onChange={e => handleLineItemChange(index, 'quantity_cartons', e.target.value)} placeholder="0" className="w-full"/></TableCell>
                                 <TableCell><Input type="number" step="0.01" value={item.price || ''} onChange={e => handleLineItemChange(index, 'price', e.target.value)} required placeholder="0.00" className="w-full"/></TableCell>
                                 <TableCell>
                                     <Select value={item.price_per_type} onValueChange={v => handleLineItemChange(index, 'price_per_type', v as PricePerTypeEnum)}>
                                         <SelectTrigger><SelectValue /></SelectTrigger>
                                         <SelectContent>
                                             {Object.values(PricePerTypeEnum).map(ppt => <SelectItem key={ppt} value={ppt}>{ppt}</SelectItem>)}
                                         </SelectContent>
                                     </Select>
                                 </TableCell>
                                 <TableCell>
                                     <Input value={item.currency || ''} readOnly disabled className="w-full bg-muted/50 border-dashed"/>
                                 </TableCell>
                                 <TableCell className="text-right font-medium">{item.currency || currency} {calculateLineItemTotal(item).toFixed(2)}</TableCell>
                                 <TableCell>
                                     <Button type="button" variant="ghost" size="icon" onClick={() => handleRemoveLineItem(item._temp_id, item.id)} 
                                        disabled={lineItems.length <= 1 && !isEditMode}
                                        className={lineItems.length <= 1 && !isEditMode ? "cursor-not-allowed opacity-50" : "hover:bg-destructive/10"}
                                     >
                                         <Trash2Icon className="h-4 w-4 text-destructive" />
                                     </Button>
                                 </TableCell>
                             </TableRow>
                             ))}
                         </TableBody>
                     </Table>
                     <Button type="button" variant="outline" size="sm" onClick={handleAddLineItem} className="mt-4">
                         <PlusCircleIcon className="mr-2 h-4 w-4" /> Add Line Item
                     </Button>
                 </CardContent>
             </Card>

             <Card>
                 <CardHeader><CardTitle>Summary & Notes</CardTitle></CardHeader>
                 <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
                     <div className="space-y-4">
                         <div>
                            <Label htmlFor="tax_percentage">Tax % (e.g., 10 for 10%)</Label>
                            <Input id="tax_percentage" type="number" step="0.01" min="0" value={taxPercentage} onChange={e => setTaxPercentage(e.target.value)} className="mt-1" />
                         </div>
                         <div>
                            <Label htmlFor="discount_percentage">Discount % (e.g., 5 for 5%)</Label>
                            <Input id="discount_percentage" type="number" step="0.01" min="0" value={discountPercentage} onChange={e => setDiscountPercentage(e.target.value)} className="mt-1" />
                         </div>
                     </div>
                     <div className="space-y-2 text-sm border p-4 rounded-md bg-muted/20">
                         <div className="flex justify-between"><span>Subtotal:</span> <span className="font-semibold">{currency} {calculatedSubtotal.toFixed(2)}</span></div>
                         <div className="flex justify-between"><span>Tax Amount:</span> <span className="font-semibold">{currency} {calculatedTax.toFixed(2)}</span></div>
                         <div className="flex justify-between"><span>Discount Amount:</span> <span className="font-semibold text-destructive">-{currency} {calculatedDiscount.toFixed(2)}</span></div>
                         <div className="flex justify-between text-lg font-bold border-t pt-2 mt-2"><span>Total:</span> <span className="font-extrabold">{currency} {calculatedTotal.toFixed(2)}</span></div>
                     </div>
                     <div className="md:col-span-2">
                         <Label htmlFor="comments_notes">Comments / Notes</Label>
                         <Textarea id="comments_notes" value={commentsNotes} onChange={e => setCommentsNotes(e.target.value)} className="mt-1" rows={3} />
                     </div>
                 </CardContent>
                 <CardFooter className="flex justify-end gap-3 pt-6">
                     <Button type="button" variant="outline" onClick={() => navigate('/invoices')} disabled={isLoading}>Cancel</Button>
                     <Button type="submit" disabled={isLoading}>
                         {isLoading ? (isEditMode ? 'Saving Invoice...' : 'Creating Invoice...') : (isEditMode ? 'Save Changes' : 'Create Invoice')}
                     </Button>
                 </CardFooter>
             </Card>
             {error && <p className="text-sm text-destructive text-center mt-4">{error}</p>}
         </form>
     </div>
  );
};

export default InvoiceEditorPage;