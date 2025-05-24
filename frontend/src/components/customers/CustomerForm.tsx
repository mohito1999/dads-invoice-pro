// src/components/customers/CustomerForm.tsx
import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea"; // Add if needed: npx shadcn@latest add textarea
import apiClient from '@/services/apiClient';
import { Customer } from '@/types';
import { useOrg } from '@/contexts/OrgContext'; // To get active organization_id

interface CustomerFormData {
  company_name: string;
  poc_name?: string;
  billing_address_line1?: string;
  billing_city?: string;
  email?: string;
  phone_number?: string;
  // Add all other relevant fields from CustomerCreate schema
}

interface CustomerFormProps {
  mode: 'create' | 'edit';
  initialData?: Customer; // Provided in 'edit' mode
  onSuccess: (processedCustomer: Customer) => void;
  onCancel: () => void;
}

const CustomerForm = ({ mode, initialData, onSuccess, onCancel }: CustomerFormProps) => {
  const { activeOrganization } = useOrg();
  const [formData, setFormData] = useState<CustomerFormData>({
    company_name: '',
    poc_name: '',
    billing_address_line1: '',
    billing_city: '',
    email: '',
    phone_number: '',
  });

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setFormData({
        company_name: initialData.company_name || '',
        poc_name: initialData.poc_name || '',
        billing_address_line1: initialData.billing_address_line1 || '',
        billing_city: initialData.billing_city || '',
        email: initialData.email || '',
        phone_number: initialData.phone_number || '',
        // Populate other fields
      });
    } else {
      setFormData({ 
        company_name: '', poc_name: '', billing_address_line1: '', 
        billing_city: '', email: '', phone_number: '' 
      });
    }
  }, [mode, initialData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mode === 'create' && !activeOrganization?.id) {
      setError("No active organization selected to create customer under.");
      return;
    }
    setIsLoading(true);
    setError(null);

    const apiData = {
      ...Object.fromEntries(
        Object.entries(formData).map(([key, value]) => [key, value === '' ? undefined : value])
      ),
      // For create mode, add organization_id. For edit, backend doesn't expect/need it in payload.
      ...(mode === 'create' && activeOrganization?.id && { organization_id: activeOrganization.id }),
    };
    
    try {
      let response;
      if (mode === 'edit' && initialData?.id) {
        response = await apiClient.put<Customer>(`/customers/${initialData.id}`, apiData);
      } else {
        response = await apiClient.post<Customer>('/customers/', apiData);
      }
      onSuccess(response.data);
    } catch (err: any) {
      console.error(`Failed to ${mode} customer:`, err);
      setError(err.response?.data?.detail || `Failed to ${mode} customer.`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="company_name">Company Name</Label>
        <Input id="company_name" name="company_name" value={formData.company_name} onChange={handleChange} required disabled={isLoading} className="mt-2" />
      </div>
      <div>
        <Label htmlFor="poc_name">POC Name</Label>
        <Input id="poc_name" name="poc_name" value={formData.poc_name} onChange={handleChange} disabled={isLoading} className="mt-2" />
      </div>
      <div>
        <Label htmlFor="email">Email</Label>
        <Input id="email" name="email" type="email" value={formData.email} onChange={handleChange} disabled={isLoading} className="mt-2" />
      </div>
      <div>
        <Label htmlFor="phone_number">Phone Number</Label>
        <Input id="phone_number" name="phone_number" value={formData.phone_number} onChange={handleChange} disabled={isLoading} className="mt-2" />
      </div>
      <div>
        <Label htmlFor="billing_address_line1">Address Line 1</Label>
        <Input id="billing_address_line1" name="billing_address_line1" value={formData.billing_address_line1} onChange={handleChange} disabled={isLoading} className="mt-2" />
      </div>
      <div>
        <Label htmlFor="billing_city">City</Label>
        <Input id="billing_city" name="billing_city" value={formData.billing_city} onChange={handleChange} disabled={isLoading} className="mt-2" />
      </div>
      {/* Add more fields for address, state, zip, country etc. */}

      {error && <p className="text-sm text-destructive text-center">{error}</p>}
      
      <div className="flex justify-end space-x-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>Cancel</Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? (mode === 'edit' ? 'Saving...' : 'Creating...') : (mode === 'edit' ? 'Save Changes' : 'Create Customer')}
        </Button>
      </div>
    </form>
  );
};
export default CustomerForm;