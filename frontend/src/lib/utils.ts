import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { InvoiceItemFormData, PricePerTypeEnum } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const _calculate_line_item_total = (item: Partial<InvoiceItemFormData>): number => {
  const price = parseFloat(String(item.price)) || 0;
  let quantity = 0;

  if (item.price_per_type === PricePerTypeEnum.CARTON && item.quantity_cartons) {
      quantity = parseFloat(String(item.quantity_cartons)) || 0;
  } else if (item.quantity_units) {
      quantity = parseFloat(String(item.quantity_units)) || 0;
  }
  return round(price * quantity);
};

const round = (num: number, places: number = 2): number => {
  return parseFloat(num.toFixed(places));
};

export const calculate_invoice_financials = (
  lineItemsData: Partial<InvoiceItemFormData>[],
  // invoiceCurrency: string, // Not used if all items in same currency
  taxPercentage: number | null | undefined = null,
  discountPercentage: number | null | undefined = null
): { subtotal: number; taxAmount: number; discountAmount: number; totalAmount: number } => {
  let subtotal = 0;
  lineItemsData.forEach(itemData => {
      subtotal += _calculate_line_item_total(itemData);
  });
  subtotal = round(subtotal);

  let calculatedTaxAmount = 0;
  if (taxPercentage && taxPercentage > 0) {
      calculatedTaxAmount = round(subtotal * (taxPercentage / 100.0));
  }

  let calculatedDiscountAmount = 0;
  if (discountPercentage && discountPercentage > 0) {
      calculatedDiscountAmount = round(subtotal * (discountPercentage / 100.0));
  }
  calculatedDiscountAmount = Math.min(calculatedDiscountAmount, subtotal); // Cap discount

  const total = round(subtotal + calculatedTaxAmount - calculatedDiscountAmount);

  return { 
      subtotal: subtotal, 
      taxAmount: calculatedTaxAmount, 
      discountAmount: calculatedDiscountAmount, 
      totalAmount: total 
  };
};