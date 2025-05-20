// src/types/index.ts
export interface OrganizationSummary {
    id: string; // UUIDs are strings
    name: string;
    logo_url?: string | null;
// Add other fields if your OrganizationSummary schema from backend includes more
}
export interface Organization extends OrganizationSummary {
    address_line1?: string | null;
    address_line2?: string | null;
    city?: string | null;
    state_province_region?: string | null;
    zip_code?: string | null;
    country?: string | null;
    contact_email?: string | null;
    contact_phone?: string | null;
    user_id: string;
    // created_at: string; // from ISO string
    // updated_at: string;
}

// Add other types here as needed (User, Customer, Item, Invoice etc.)
export interface UserProfile {
    id: string;
    email: string;
    full_name?: string | null;
    is_active: boolean;
}

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

export interface ItemSummary {
    id: string;
    name: string;
    default_price?: number | null;
    default_unit?: string | null;
    image_url?: string | null;
    // Add other fields from your ItemSummary schema if any
}
  
export interface Item extends ItemSummary {
    organization_id: string;
    description?: string | null;
    // created_at: string;
    // updated_at: string;
}
  
export enum InvoiceTypeEnum {
    PRO_FORMA = "Pro Forma",
    COMMERCIAL = "Commercial",
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
  
export interface InvoiceItem {
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
}
  
  // For creating/updating line items, similar to backend schema
export interface InvoiceItemFormData {
    id?: string; // For identifying existing items during update
    item_id?: string | null;
    item_description: string;
    quantity_cartons?: number | string | null; // string for input
    quantity_units?: number | string | null;   // string for input
    unit_type?: string | null;
    price: number | string; // string for input
    price_per_type: PricePerTypeEnum;
    currency: string;
    item_specific_comments?: string | null;
    // A temporary client-side ID for managing new items in the form before saving
    _temp_id?: string; 
}
  
  
export interface InvoiceSummary {
    id: string;
    invoice_number: string;
    invoice_date: string; // Comes as string, might need Date conversion
    customer_company_name?: string | null;
    total_amount: number;
    currency: string;
    status: InvoiceStatusEnum;
    invoice_type: InvoiceTypeEnum;
}
  
export interface Invoice extends Omit<InvoiceSummary, 'customer_company_name'> {
    organization_id: string;
    customer_id: string;
    user_id: string; // From backend if needed, or assume current user
    due_date?: string | null; // Comes as string
    subtotal_amount: number;
    tax_percentage?: number | null;
    tax_amount: number;
    discount_percentage?: number | null;
    discount_amount: number;
    amount_paid: number;
    comments_notes?: string | null;
    pdf_url?: string | null;
    line_items: InvoiceItem[];
    created_at: string; // ISO string
    updated_at: string; // ISO string
}
  
