// src/components/organizations/OrganizationForm.tsx
import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
// import { Textarea } from "@/components/ui/textarea"; // If you add it
import apiClient from '@/services/apiClient';
import { Organization, OrganizationSummary } from '@/types'; // We'll use Organization for initialData and response

interface OrganizationFormData {
  name: string;
  address_line1?: string;
  city?: string;
  contact_email?: string;
  logo_url?: string;
  // Add other fields from OrganizationCreate/Update schema
  // address_line2?: string;
  // state_province_region?: string;
  // zip_code?: string;
  // country?: string;
  // contact_phone?: string;
}

interface OrganizationFormProps {
  mode: 'create' | 'edit';
  initialData?: Organization; // Provided in 'edit' mode
  onSuccess: (updatedOrNewOrganization: Organization) => void;
  onCancel: () => void;
}

const OrganizationForm = ({ mode, initialData, onSuccess, onCancel }: OrganizationFormProps) => {
  const [formData, setFormData] = useState<OrganizationFormData>({
    name: '',
    address_line1: '',
    city: '',
    contact_email: '',
    logo_url: '',
    // Initialize other fields
  });

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setFormData({
        name: initialData.name || '',
        address_line1: initialData.address_line1 || '',
        city: initialData.city || '',
        contact_email: initialData.contact_email || '',
        logo_url: initialData.logo_url || '',
        // Populate other fields from initialData
      });
    } else {
      // Reset form for create mode or if initialData is missing in edit mode (should not happen)
      setFormData({ 
        name: '', 
        address_line1: '', 
        city: '', 
        contact_email: '', 
        logo_url: '' 
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

    // Prepare data for API, sending undefined for empty optional strings
    const apiData = Object.fromEntries(
      Object.entries(formData).map(([key, value]) => [key, value === '' ? undefined : value])
    );

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
        <Label htmlFor="name">Organization Name</Label>
        <Input
          id="name"
          name="name" // Add name attribute for handleChange
          value={formData.name}
          onChange={handleChange}
          required
          disabled={isLoading}
          placeholder="e.g., Dad's Awesome Co."
          className="mt-1"
        />
      </div>
      <div>
        <Label htmlFor="address_line1">Address Line 1</Label>
        <Input
          id="address_line1"
          name="address_line1" // Add name attribute
          value={formData.address_line1}
          onChange={handleChange}
          disabled={isLoading}
          className="mt-1"
        />
      </div>
      <div>
        <Label htmlFor="city">City</Label>
        <Input
          id="city"
          name="city" // Add name attribute
          value={formData.city}
          onChange={handleChange}
          disabled={isLoading}
          className="mt-1"
        />
      </div>
      <div>
        <Label htmlFor="contact_email">Contact Email</Label>
        <Input
          id="contact_email"
          name="contact_email" // Add name attribute
          type="email"
          value={formData.contact_email}
          onChange={handleChange}
          disabled={isLoading}
          className="mt-1"
        />
      </div>
      <div>
        <Label htmlFor="logo_url">Logo URL</Label>
        <Input
          id="logo_url"
          name="logo_url" // Add name attribute
          type="url"
          value={formData.logo_url}
          onChange={handleChange}
          placeholder="https://example.com/logo.png"
          disabled={isLoading}
          className="mt-1"
        />
      </div>
      {/* Add more fields here, ensuring each Input has a 'name' attribute matching a key in OrganizationFormData */}

      {error && <p className="text-sm text-destructive text-center">{error}</p>}
      
      <div className="flex justify-end space-x-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading 
            ? (mode === 'edit' ? 'Saving...' : 'Creating...') 
            : (mode === 'edit' ? 'Save Changes' : 'Create Organization')}
        </Button>
      </div>
    </form>
  );
};

export default OrganizationForm;