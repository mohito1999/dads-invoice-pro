// src/types/index.ts

// --- Organization Types ---
export interface OrganizationSummary {
    id: string;
    name: string;
    logo_url?: string | null;
    contact_email?: string | null;
}
export interface Organization extends OrganizationSummary {
    address_line1?: string | null;
    address_line2?: string | null;
    city?: string | null;
    state_province_region?: string | null;
    zip_code?: string | null;
    country?: string | null;
    contact_phone?: string | null;
    user_id: string;
}

// MODIFIED OrganizationFormData
export interface OrganizationFormData {
  name: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province_region?: string;
  zip_code?: string;
  country?: string;
  contact_email?: string;
  contact_phone?: string;
  // logo_url is removed, will be handled by File state in the form
}

// ... (rest of your types/index.ts file remains the same) ...

// --- User Profile ---
export interface UserProfile {
    id: string;
    email: string;
    full_name?: string | null;
    is_active: boolean;
}

// --- Customer Types ---
export interface CustomerSummary {
  id: string;
  company_name: string;
  poc_name?: string | null;
  email?: string | null;
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
}

// --- Item Types ---
export interface ItemImage { 
  id: string;
  image_url: string;
  order_index: number;
  alt_text?: string | null; 
}

export interface ItemSummary { 
    id: string;
    name: string;
    description?: string | null; 
    default_price?: number | null;
    default_unit?: string | null;
    image_url?: string | null; 
}
  
export interface Item { 
    id: string;
    organization_id: string;
    name: string;
    description?: string | null;
    default_price?: number | null;
    default_unit?: string | null;
    images: ItemImage[]; 
}

export interface ItemFormData { 
    name: string;
    description?: string;
    default_price?: number | string; 
    default_unit?: string;
}


// --- Invoice Related Enums ---
export enum InvoiceTypeEnum {
    PRO_FORMA = "PRO_FORMA",
    COMMERCIAL = "COMMERCIAL",
    PACKING_LIST = "PACKING_LIST",
}

export enum InvoiceStatusEnum {
    DRAFT = "DRAFT",
    UNPAID = "UNPAID",
    PAID = "PAID",
    PARTIALLY_PAID = "PARTIALLY_PAID",
    OVERDUE = "OVERDUE",
    CANCELLED = "CANCELLED",
}

export enum PricePerTypeEnum {
    UNIT = "UNIT",
    CARTON = "CARTON",
}
  
// --- Invoice Item Types ---
export interface InvoiceItem extends Omit<InvoiceItemFormData, '_temp_id' | 'price' | 'quantity_cartons' | 'quantity_units' | 'net_weight_kgs' | 'gross_weight_kgs' | 'measurement_cbm'> {
    id: string; 
    invoice_id: string;
    line_total: number;
    price: number; 
    quantity_cartons?: number | null; 
    quantity_units?: number | null;   
    net_weight_kgs?: number | null;
    gross_weight_kgs?: number | null;
    measurement_cbm?: number | null;
  }
  
export interface InvoiceItemFormData { 
    id?: string; 
    _temp_id?: string; 
    item_id?: string | null; 
    item_description: string;
    quantity_cartons?: number | string | null; 
    quantity_units?: number | string | null;   
    unit_type?: string | null;
    price: number | string; 
    price_per_type: PricePerTypeEnum;
    currency: string;
    item_specific_comments?: string | null;
    net_weight_kgs?: number | string | null;
    gross_weight_kgs?: number | string | null;
    measurement_cbm?: number | string | null;
}
  
// --- Invoice Types ---
export interface InvoiceSummary { 
    id: string;
    invoice_number: string;
    invoice_date: string; 
    customer_company_name?: string | null; 
    total_amount: number;
    currency: string;
    status: InvoiceStatusEnum;
    invoice_type: InvoiceTypeEnum;
}
  
export interface Invoice {
    id: string;
    organization_id: string;
    customer_id: string;
    user_id: string; 
    invoice_number: string;
    invoice_date: string; 
    due_date?: string | null; 
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
    pdf_url?: string | null; 
    line_items: InvoiceItem[];
    created_at: string; 
    updated_at: string; 
    container_number?: string | null;
    seal_number?: string | null;
    hs_code?: string | null;
    bl_number?: string | null;
}

export interface InvoiceCreateData extends Omit<Invoice, 
    'id' | 'user_id' | 'pdf_url' | 'created_at' | 'updated_at' | 
    'subtotal_amount' | 'tax_amount' | 'total_amount' | 'amount_paid' | 'line_items'
> {
    organization_id: string; 
    line_items: Omit<InvoiceItemFormData, 'id' | '_temp_id'>[]; 
}

export interface InvoiceUpdateData extends Partial<Omit<InvoiceCreateData, 'organization_id'>> {
    line_items?: Omit<InvoiceItemFormData, '_temp_id'>[];
}

export interface DashboardStats {
    total_invoiced_amount: number;
    total_collected_amount: number;
    total_outstanding_amount: number;
    count_overdue_invoices: number;
    currency?: string | null;
}