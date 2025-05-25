// src/components/organizations/OrganizationForm.tsx
import { useState, useEffect, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import apiClient from '@/services/apiClient';
import { Organization, OrganizationFormData } from '@/types'; // OrganizationFormData updated
import { ImagePlus, Trash2, XCircle } from 'lucide-react'; // Icons
import { toast } from 'sonner';
import { getFullStaticUrl } from '@/config'; // For displaying existing logo

interface OrganizationFormProps {
  mode: 'create' | 'edit';
  initialData?: Organization; 
  onSuccess: (organization: Organization) => void;
  onCancel: () => void;
}

const OrganizationForm = ({ mode, initialData, onSuccess, onCancel }: OrganizationFormProps) => {
  const [formData, setFormData] = useState<OrganizationFormData>({ // Now excludes logo_url
    name: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state_province_region: '',
    zip_code: '',
    country: '',
    contact_email: '',
    contact_phone: '',
  });

  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null); // For new logo preview
  const [existingLogoUrl, setExistingLogoUrl] = useState<string | null>(null); // For current logo
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false); // General loading for text data
  const [isUploadingLogo, setIsUploadingLogo] = useState(false); // Specific for logo upload

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
        contact_phone: initialData.contact_phone || '',
      });
      setExistingLogoUrl(initialData.logo_url || null);
      setLogoFile(null); // Clear any selected file
      setLogoPreview(null); // Clear preview
    } else {
      setFormData({
        name: '', address_line1: '', address_line2: '', city: '',
        state_province_region: '', zip_code: '', country: '',
        contact_email: '', contact_phone: '',
      });
      setExistingLogoUrl(null);
      setLogoFile(null);
      setLogoPreview(null);
    }
  }, [mode, initialData]);

  // Effect to clear object URL for logoPreview
  useEffect(() => {
    return () => {
      if (logoPreview) {
        URL.revokeObjectURL(logoPreview);
      }
    };
  }, [logoPreview]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleLogoFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];
      setLogoFile(file);
      if (logoPreview) URL.revokeObjectURL(logoPreview); // Revoke old preview
      setLogoPreview(URL.createObjectURL(file));
      setExistingLogoUrl(null); // If new file is selected, hide existing logo preview
    }
  };

  const removeNewLogo = () => {
    if (logoPreview) URL.revokeObjectURL(logoPreview);
    setLogoFile(null);
    setLogoPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = ""; // Reset file input
    // If editing, restore existing logo preview if it was there
    if (mode === 'edit' && initialData?.logo_url) {
      setExistingLogoUrl(initialData.logo_url);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true); // For text data submission
    setError(null);

    const apiPayload: any = { name: formData.name };
    for (const key in formData) {
      if (key !== 'name' && Object.prototype.hasOwnProperty.call(formData, key)) {
        const typedKey = key as keyof Omit<OrganizationFormData, 'name'>;
        const value = formData[typedKey];
        if (typeof value === 'string' && value.trim() === '') {
          apiPayload[typedKey] = null; 
        } else if (value !== undefined && value !== '') { 
          apiPayload[typedKey] = value;
        }
      }
    }

    try {
      let organizationData: Organization;
      // Step 1: Create or Update Organization Text Data
      if (mode === 'edit' && initialData?.id) {
        const response = await apiClient.put<Organization>(`/organizations/${initialData.id}`, apiPayload);
        organizationData = response.data;
      } else {
        const response = await apiClient.post<Organization>('/organizations/', apiPayload);
        organizationData = response.data;
      }
      toast.success(`Organization "${organizationData.name}" details ${mode === 'create' ? 'created' : 'updated'}.`);

      // Step 2: Upload Logo if a new one is selected
      if (logoFile && organizationData.id) {
        setIsUploadingLogo(true);
        const logoFormData = new FormData();
        logoFormData.append('logo_file', logoFile);
        try {
          const logoResponse = await apiClient.post<Organization>(
            `/organizations/${organizationData.id}/upload-logo`,
            logoFormData,
            { headers: { 'Content-Type': 'multipart/form-data' } }
          );
          organizationData = logoResponse.data; // Update with response that includes new logo_url
          toast.success('Logo uploaded successfully!');
        } catch (logoErr: any) {
          console.error("Failed to upload logo:", logoErr);
          toast.error(logoErr.response?.data?.detail || "Failed to upload logo. Organization details were saved.");
          // Proceed with organizationData from step 1 if logo upload fails
        } finally {
          setIsUploadingLogo(false);
        }
      }
      onSuccess(organizationData); // Call onSuccess with the final organization data

    } catch (err: any) {
      console.error(`Failed to ${mode} organization:`, err);
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((e: { loc: string[], msg: string }) => `${e.loc.join('.')} - ${e.msg}`).join('; '));
      } else {
        setError(detail || `Failed to ${mode} organization.`);
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  const totalLoading = isLoading || isUploadingLogo;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <Label htmlFor="name">Organization Name <span className="text-destructive">*</span></Label>
        <Input id="name" name="name" value={formData.name} onChange={handleChange} required disabled={totalLoading} className="mt-2" />
      </div>
      
      {/* Logo Upload Section */}
      <div>
        <Label htmlFor="logo-upload">Organization Logo</Label>
        <div className="mt-2 flex items-center gap-4">
          <div className="w-24 h-24 border border-dashed rounded-md flex items-center justify-center bg-muted overflow-hidden">
            {logoPreview ? (
              <img src={logoPreview} alt="New logo preview" className="w-full h-full object-contain" />
            ) : existingLogoUrl ? (
              <img src={getFullStaticUrl(existingLogoUrl)} alt="Current logo" className="w-full h-full object-contain" />
            ) : (
              <ImagePlus className="w-10 h-10 text-gray-400" strokeWidth={1} />
            )}
          </div>
          <div className="flex flex-col gap-2">
            <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()} disabled={totalLoading}>
              {logoFile || existingLogoUrl ? 'Change Logo' : 'Upload Logo'}
            </Button>
            {(logoFile || (mode === 'edit' && existingLogoUrl)) && (
                 <Button type="button" variant="ghost" size="sm" onClick={removeNewLogo} disabled={totalLoading} className="text-xs text-destructive hover:text-destructive/80">
                    <XCircle className="mr-1 h-3 w-3" />
                    {logoFile ? 'Remove selection' : 'Clear current logo (save to remove)'} 
                    {/* Clarify that clearing existing logo requires saving */}
                 </Button>
            )}
          </div>
          <input
            type="file"
            id="logo-upload"
            ref={fileInputRef}
            className="hidden"
            accept="image/png, image/jpeg, image/gif, image/webp, image/svg+xml"
            onChange={handleLogoFileChange}
            disabled={totalLoading}
          />
        </div>
         {mode === 'edit' && existingLogoUrl && !logoFile && <p className="text-xs text-muted-foreground mt-2">To remove the current logo, clear the selection and save changes (or upload a new one).</p>}
      </div>


      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="contact_email">Contact Email</Label>
          <Input id="contact_email" name="contact_email" type="email" value={formData.contact_email} onChange={handleChange} disabled={totalLoading} className="mt-2" />
        </div>
        <div> 
          <Label htmlFor="contact_phone">Contact Phone</Label>
          <Input id="contact_phone" name="contact_phone" type="tel" value={formData.contact_phone} onChange={handleChange} disabled={totalLoading} className="mt-2" />
        </div>
      </div>

      <div>
        <Label htmlFor="address_line1">Address Line 1</Label>
        <Input id="address_line1" name="address_line1" value={formData.address_line1} onChange={handleChange} disabled={totalLoading} className="mt-2" />
      </div>
      <div>
        <Label htmlFor="address_line2">Address Line 2</Label>
        <Input id="address_line2" name="address_line2" value={formData.address_line2} onChange={handleChange} disabled={totalLoading} className="mt-2" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <Label htmlFor="city">City</Label>
          <Input id="city" name="city" value={formData.city} onChange={handleChange} disabled={totalLoading} className="mt-2" />
        </div>
        <div>
          <Label htmlFor="state_province_region">State/Province/Region</Label>
          <Input id="state_province_region" name="state_province_region" value={formData.state_province_region} onChange={handleChange} disabled={totalLoading} className="mt-2" />
        </div>
        <div>
          <Label htmlFor="zip_code">Zip/Postal Code</Label>
          <Input id="zip_code" name="zip_code" value={formData.zip_code} onChange={handleChange} disabled={totalLoading} className="mt-2" />
        </div>
      </div>
      <div>
        <Label htmlFor="country">Country</Label>
        <Input id="country" name="country" value={formData.country} onChange={handleChange} disabled={totalLoading} className="mt-2" />
      </div>
      {/* logo_url input removed */}

      {error && <p className="text-sm text-destructive text-center">{error}</p>}
      
      <div className="flex justify-end space-x-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={totalLoading}>Cancel</Button>
        <Button type="submit" disabled={totalLoading}>
          {isLoading ? 'Saving Details...' : isUploadingLogo ? 'Uploading Logo...' : (mode === 'edit' ? 'Save Changes' : 'Create Organization')}
        </Button>
      </div>
    </form>
  );
};
export default OrganizationForm;