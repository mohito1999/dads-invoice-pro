// src/components/organizations/OrganizationForm.tsx
import React, { useState, useEffect, useRef, useMemo } from 'react'; // Added React for useMemo
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import apiClient from '@/services/apiClient';
import { Organization, OrganizationFormData, InvoiceTemplateSummary } from '@/types';
import { ImagePlus, Trash2, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { getFullStaticUrl } from '@/config';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface OrganizationFormProps {
  mode: 'create' | 'edit';
  initialData?: Organization;
  onSuccess: (organization: Organization) => void;
  onCancel: () => void;
}

const USE_SYSTEM_DEFAULT_OPTION_VALUE = "---SYSTEM_DEFAULT---";

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
    contact_phone: '',
    selected_invoice_template_id: null, // Initialize with null
  });

  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [existingLogoUrl, setExistingLogoUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploadingLogo, setIsUploadingLogo] = useState(false);

  const [availableTemplates, setAvailableTemplates] = useState<InvoiceTemplateSummary[]>([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false);

  // Friend's Feedback Point 1 & 3 (useEffect for initial data and debugging initialData)
  useEffect(() => {
    if (mode === 'edit' && initialData) {
      // Debugging initialData (Friend's Feedback Point 3)
      console.log('Initial data received for OrganizationForm:', {
        selected_invoice_template_id: initialData.selected_invoice_template_id,
        type: typeof initialData.selected_invoice_template_id,
      });

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
        // Fix: Handle null, undefined, and empty string properly for initialization (Friend's Feedback Point 1)
        selected_invoice_template_id: initialData.selected_invoice_template_id || null,
      });
      setExistingLogoUrl(initialData.logo_url || null);
      setLogoFile(null);
      setLogoPreview(null);
    } else { // Create mode
      setFormData({
        name: '', address_line1: '', address_line2: '', city: '',
        state_province_region: '', zip_code: '', country: '',
        contact_email: '', contact_phone: '',
        selected_invoice_template_id: null, // Default to null (represents system default choice)
      });
      setExistingLogoUrl(null);
      setLogoFile(null);
      setLogoPreview(null);
    }
  }, [mode, initialData]);

  useEffect(() => {
    const fetchTemplates = async () => {
      setIsLoadingTemplates(true);
      try {
        const response = await apiClient.get<InvoiceTemplateSummary[]>('/invoice-templates/');
        setAvailableTemplates(response.data);
      } catch (err) {
        console.error("Failed to fetch invoice templates:", err);
        toast.error("Could not load invoice templates for selection.");
        setAvailableTemplates([]);
      } finally {
        setIsLoadingTemplates(false);
      }
    };
    fetchTemplates();
  }, []);

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

  const handleTemplateChange = (selectedValue: string) => {
    if (selectedValue === USE_SYSTEM_DEFAULT_OPTION_VALUE) {
      setFormData(prev => ({ ...prev, selected_invoice_template_id: null }));
    } else {
      setFormData(prev => ({ ...prev, selected_invoice_template_id: selectedValue }));
    }
  };

  const handleLogoFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];
      setLogoFile(file);
      if (logoPreview) URL.revokeObjectURL(logoPreview);
      setLogoPreview(URL.createObjectURL(file));
      setExistingLogoUrl(null);
    }
  };

  const removeNewLogo = () => {
    if (logoPreview) URL.revokeObjectURL(logoPreview);
    setLogoFile(null);
    setLogoPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (mode === 'edit' && initialData?.logo_url) {
      setExistingLogoUrl(initialData.logo_url);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    const apiPayload = {
      ...Object.fromEntries(
        Object.entries(formData)
          .filter(([key]) => key !== 'selected_invoice_template_id')
          .map(([key, value]) => [key, (typeof value === 'string' && value.trim() === '') ? null : value])
      ),
      selected_invoice_template_id: formData.selected_invoice_template_id, // Already null or UUID string
    };

    try {
      let organizationData: Organization;
      if (mode === 'edit' && initialData?.id) {
        const response = await apiClient.put<Organization>(`/organizations/${initialData.id}`, apiPayload);
        organizationData = response.data;
      } else {
        const response = await apiClient.post<Organization>('/organizations/', apiPayload);
        organizationData = response.data;
      }
      toast.success(`Organization "${organizationData.name}" details ${mode === 'create' ? 'created' : 'updated'}.`);

      if (logoFile && organizationData.id) {
        setIsUploadingLogo(true);
        const logoFormDataPayload = new FormData();
        logoFormDataPayload.append('logo_file', logoFile);
        try {
          const logoResponse = await apiClient.post<Organization>(
            `/organizations/${organizationData.id}/upload-logo`,
            logoFormDataPayload,
            { headers: { 'Content-Type': 'multipart/form-data' } }
          );
          organizationData = logoResponse.data;
          toast.success('Logo uploaded successfully!');
        } catch (logoErr: any) {
          console.error("Failed to upload logo:", logoErr);
          toast.error(logoErr.response?.data?.detail || "Failed to upload logo. Organization details were saved.");
        } finally {
          setIsUploadingLogo(false);
        }
      }
      onSuccess(organizationData);

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

  const totalLoading = isLoading || isUploadingLogo || isLoadingTemplates;

  // Friend's Feedback Point 2 (useMemo for selectValue with debugging)
  const selectValue = useMemo(() => {
    const templateId = formData.selected_invoice_template_id;
    
    // Debug logging (can be removed in production)
    // console.log('DEBUG: formData.selected_invoice_template_id:', templateId, '| Type:', typeof templateId);
    // console.log('DEBUG: Available templates IDs:', availableTemplates.map(t => t.id));
    
    if (!templateId) { // Handles null, undefined, or empty string (though should primarily be null)
      // console.log('DEBUG: No templateId found in formData, defaulting to USE_SYSTEM_DEFAULT_OPTION_VALUE');
      return USE_SYSTEM_DEFAULT_OPTION_VALUE;
    }

    if (isLoadingTemplates) {
      return templateId;
    }
    
    const templateExists = availableTemplates.some(t => t.id === templateId);
    if (templateExists) {
      // console.log('DEBUG: templateId found in availableTemplates, using ID:', templateId);
      return templateId;
    } else {
      // This case could happen if a template was selected, then deleted from the system,
      // and the organization still has the old ID.
      // console.warn('DEBUG: templateId from formData NOT found in available templates, defaulting to USE_SYSTEM_DEFAULT_OPTION_VALUE. ID was:', templateId);
      return USE_SYSTEM_DEFAULT_OPTION_VALUE;
    }
  }, [formData.selected_invoice_template_id, availableTemplates]);


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

      {/* Invoice Template Selector (Friend's Feedback Point 4) */}
      <div>
        <Label htmlFor="invoice-template-select">Default Invoice Template</Label>
        <Select
          value={selectValue} // Use the memoized and debugged selectValue
          onValueChange={handleTemplateChange}
          disabled={totalLoading || isLoadingTemplates}
        >
          <SelectTrigger id="invoice-template-select" className="mt-2 w-full">
            <SelectValue 
              placeholder={
                isLoadingTemplates 
                  ? "Loading templates..." 
                  : "Select a template..."
              } 
            />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={USE_SYSTEM_DEFAULT_OPTION_VALUE}>
              Use System Default Template
            </SelectItem>
            {availableTemplates.map((template) => (
              <SelectItem key={template.id} value={template.id}>
                {template.name} {template.is_system_default && "(System Default)"}
              </SelectItem>
            ))}
            {availableTemplates.length === 0 && !isLoadingTemplates && (
              <SelectItem value="no-templates-available" disabled>
                No custom templates available
              </SelectItem>
            )}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground mt-1">
          Select a default template for invoices generated by this organization. If none is chosen, the system default will be used.
        </p>
      </div>

      {/* Contact and Address Fields */}
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