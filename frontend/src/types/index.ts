// src/types/index.ts

// --- Organization Types ---
export interface OrganizationSummary {
    id: string; // UUIDs are strings
    name: string;
    logo_url?: string | null;
    contact_email?: string | null; // Added as per OrganizationsPage table
// Add other fields if your OrganizationSummary schema from backend includes more
}
export interface Organization extends OrganizationSummary {
    address_line1?: string | null;
    address_line2?: string | null;
    city?: string | null;
    state_province_region?: string | null;
    zip_code?: string | null;
    country?: string | null;
    // contact_email is already in OrganizationSummary
    contact_phone?: string | null;
    user_id: string;
    // created_at: string; // from ISO string
    // updated_at: string;
}

// --- User Profile ---
export interface UserProfile {
    id: string;
    email: string;
    full_name?: string | null;
    is_active: boolean;
    // Add is_superuser if you use it on frontend
}

// --- Customer Types ---
export interface CustomerSummary {
  id: string;
  company_name: string;
  poc_name?: string | null;
  email?: string | null;
  // Add other fields from your CustomerSummary schema if any
}

export interface Customer extends CustomerSummary {
  organization_id: string;
  billing_address_line1?: string | null;
  billing_address_line2?: string | null;
  billing_city?: string | null;
  billing_state_province_region?: string | null;
  billing_zip_code?: string | null;
  billing_country?: string | null;
  phone_number?: string | null;
  // created_at: string;
  // updated_at: string;
}

// --- Item Types ---
export interface ItemSummary {
    id: string;
    name: string;
    description?: string | null; // Added as per ItemsPage table
    default_price?: number | null;
    default_unit?: string | null;
    image_url?: string | null;
    // Add other fields from your ItemSummary schema if any
}
  
export interface Item extends ItemSummary {
    organization_id: string;
    // description is already in ItemSummary
    // created_at: string;
    // updated_at: string;
}

// --- Invoice Related Enums ---
export enum InvoiceTypeEnum {
    PRO_FORMA = "Pro Forma",
    COMMERCIAL = "Commercial",
    // PACKING_LIST = "Packing List", // Example, if you add more
}
  
export enum InvoiceStatusEnum {
    DRAFT = "Draft",
    UNPAID = "Unpaid",
    PAID = "Paid",
    PARTIALLY_PAID = "Partially Paid",
    OVERDUE = "Overdue",
    CANCELLED = "Cancelled",
}
  
export enum PricePerTypeEnum {
    UNIT = "unit",
    CARTON = "carton",
}
  
// --- Invoice Item Types ---
export interface InvoiceItem { // For data coming from backend / display
    id: string; // UUID
    invoice_id: string; // UUID
    item_id?: string | null; // UUID, link to a predefined item
    item_description: string;
    quantity_cartons?: number | null;
    quantity_units?: number | null;
    unit_type?: string | null;
    price: number;
    price_per_type: PricePerTypeEnum;
    currency: string;
    item_specific_comments?: string | null;
    line_total: number;
    // If you link the full Item object in backend for PDF/View, you might add:
    // item?: ItemSummary | null; 
}
  
export interface InvoiceItemFormData { // For forms
    id?: string; // For identifying existing items during update
    _temp_id?: string; // Client-side temporary ID for managing new items in the form key prop
    item_id?: string | null; // Can be actual ID or ITEM_PLACEHOLDER_VALUE
    item_description: string;
    quantity_cartons?: number | string | null; // string for input, number for processing
    quantity_units?: number | string | null;   // string for input
    unit_type?: string | null;
    price: number | string; // string for input
    price_per_type: PricePerTypeEnum;
    currency: string;
    item_specific_comments?: string | null;
}
  
// --- Invoice Types ---
export interface InvoiceSummary { // For lists
    id: string;
    invoice_number: string;
    invoice_date: string; // Comes as string "YYYY-MM-DD"
    customer_company_name?: string | null; // Denormalized for easy display
    total_amount: number;
    currency: string;
    status: InvoiceStatusEnum;
    invoice_type: InvoiceTypeEnum;
}
  
// Full Invoice type for detail views and editing (matches backend schema)
export interface Invoice {
    id: string;
    organization_id: string;
    customer_id: string;
    user_id: string; 
    invoice_number: string;
    invoice_date: string; // "YYYY-MM-DD"
    due_date?: string | null; // "YYYY-MM-DD"
    invoice_type: InvoiceTypeEnum;
    status: InvoiceStatusEnum;
    currency: string;
    subtotal_amount: number;
    tax_percentage?: number | null;
    tax_amount: number;
    discount_percentage?: number | null;
    discount_amount: number;
    total_amount: number;
    amount_paid: number;
    comments_notes?: string | null;
    pdf_url?: string | null; // Should be HttpUrl if using Pydantic's HttpUrl
    line_items: InvoiceItem[];
    created_at: string; // ISO datetime string
    updated_at: string; // ISO datetime string

    // --- ADDED NEW FIELDS as per feedback ---
    container_number?: string | null;
    seal_number?: string | null;
    hs_code?: string | null;
    // --- END ADDED NEW FIELDS ---
}

// This combines base fields from backend's InvoiceCreate into what frontend sends.
// Backend's InvoiceCreate excludes calculated fields; frontend form collects all.
export interface InvoiceCreateData extends Omit<Invoice, 
    'id' | 'user_id' | 'pdf_url' | 'created_at' | 'updated_at' | 
    'subtotal_amount' | 'tax_amount' | 'total_amount' | 'amount_paid' | 'line_items' // these are calculated or special
> {
    organization_id: string; // Required for creation by frontend logic
    line_items: Omit<InvoiceItemFormData, 'id' | '_temp_id'>[]; // Send data for new line items
}

// For updating, most fields are optional.
export interface InvoiceUpdateData extends Partial<Omit<InvoiceCreateData, 'organization_id'>> {
    line_items?: Omit<InvoiceItemFormData, '_temp_id'>[]; // For full replacement of line items
}