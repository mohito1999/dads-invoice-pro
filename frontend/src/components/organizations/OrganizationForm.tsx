// src/components/organizations/OrganizationForm.tsx
import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea"; // Assuming you might want it for description later
import apiClient from '@/services/apiClient';
import { Organization } from '@/types'; // Full Organization type for initialData & onSuccess
// No direct use of useOrg here unless for default org_id, but page passes it or it's an update.

interface OrganizationFormData {
  name: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state_province_region?: string;
  zip_code?: string;
  country?: string;
  contact_email?: string;
  contact_phone?: string; // New field
  logo_url?: string;
}

interface OrganizationFormProps {
  mode: 'create' | 'edit';
  initialData?: Organization; // Full Organization for edit
  onSuccess: (organization: Organization) => void;
  onCancel: () => void;
}

const OrganizationForm = ({ mode, initialData, onSuccess, onCancel }: OrganizationFormProps) => {
  const [formData, setFormData] = useState<OrganizationFormData>({
    name: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state_province_region: '',
    zip_code: '',
    country: '',
    contact_email: '',
    contact_phone: '', // Initialized
    logo_url: '',
  });

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setFormData({
        name: initialData.name || '',
        address_line1: initialData.address_line1 || '',
        address_line2: initialData.address_line2 || '',
        city: initialData.city || '',
        state_province_region: initialData.state_province_region || '',
        zip_code: initialData.zip_code || '',
        country: initialData.country || '',
        contact_email: initialData.contact_email || '',
        contact_phone: initialData.contact_phone || '', // Populate from initialData
        logo_url: initialData.logo_url || '',
      });
    } else {
      // Reset for create mode
      setFormData({
        name: '', address_line1: '', address_line2: '', city: '',
        state_province_region: '', zip_code: '', country: '',
        contact_email: '', contact_phone: '', logo_url: '',
      });
    }
  }, [mode, initialData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    // Prepare data for API, ensure undefined for empty optional strings
    const apiData = {
      name: formData.name,
      address_line1: formData.address_line1 || undefined,
      address_line2: formData.address_line2 || undefined,
      city: formData.city || undefined,
      state_province_region: formData.state_province_region || undefined,
      zip_code: formData.zip_code || undefined,
      country: formData.country || undefined,
      contact_email: formData.contact_email || undefined,
      contact_phone: formData.contact_phone || undefined, // Include in API data
      logo_url: formData.logo_url || undefined,
    };

    try {
      let response;
      if (mode === 'edit' && initialData?.id) {
        response = await apiClient.put<Organization>(`/organizations/${initialData.id}`, apiData);
      } else {
        response = await apiClient.post<Organization>('/organizations/', apiData);
      }
      onSuccess(response.data);
    } catch (err: any) {
      console.error(`Failed to ${mode} organization:`, err);
      setError(err.response?.data?.detail || `Failed to ${mode} organization.`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="name">Organization Name <span className="text-destructive">*</span></Label>
        <Input id="name" name="name" value={formData.name} onChange={handleChange} required disabled={isLoading} className="mt-2" />
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="contact_email">Contact Email</Label>
          <Input id="contact_email" name="contact_email" type="email" value={formData.contact_email} onChange={handleChange} disabled={isLoading} className="mt-2" />
        </div>
        <div> {/* NEW FIELD */}
          <Label htmlFor="contact_phone">Contact Phone</Label>
          <Input id="contact_phone" name="contact_phone" type="tel" value={formData.contact_phone} onChange={handleChange} disabled={isLoading} className="mt-2" />
        </div>
      </div>

      <div>
        <Label htmlFor="address_line1">Address Line 1</Label>
        <Input id="address_line1" name="address_line1" value={formData.address_line1} onChange={handleChange} disabled={isLoading} className="mt-2" />
      </div>
      <div>
        <Label htmlFor="address_line2">Address Line 2</Label>
        <Input id="address_line2" name="address_line2" value={formData.address_line2} onChange={handleChange} disabled={isLoading} className="mt-2" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <Label htmlFor="city">City</Label>
          <Input id="city" name="city" value={formData.city} onChange={handleChange} disabled={isLoading} className="mt-2" />
        </div>
        <div>
          <Label htmlFor="state_province_region">State/Province/Region</Label>
          <Input id="state_province_region" name="state_province_region" value={formData.state_province_region} onChange={handleChange} disabled={isLoading} className="mt-2" />
        </div>
        <div>
          <Label htmlFor="zip_code">Zip/Postal Code</Label>
          <Input id="zip_code" name="zip_code" value={formData.zip_code} onChange={handleChange} disabled={isLoading} className="mt-2" />
        </div>
      </div>
      <div>
        <Label htmlFor="country">Country</Label>
        <Input id="country" name="country" value={formData.country} onChange={handleChange} disabled={isLoading} className="mt-2" />
      </div>
      <div>
        <Label htmlFor="logo_url">Logo URL (Optional)</Label>
        <Input id="logo_url" name="logo_url" type="url" value={formData.logo_url} onChange={handleChange} disabled={isLoading} className="mt-2" placeholder="https://example.com/logo.png" />
      </div>

      {error && <p className="text-sm text-destructive text-center">{error}</p>}
      
      <div className="flex justify-end space-x-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>Cancel</Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? (mode === 'edit' ? 'Saving...' : 'Creating...') : (mode === 'edit' ? 'Save Changes' : 'Create Organization')}
        </Button>
      </div>
    </form>
  );
};
export default OrganizationForm;