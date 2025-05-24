// src/components/items/ItemForm.tsx
import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import apiClient from '@/services/apiClient';
import { Item } from '@/types'; // Assuming Item type includes all fields like organization_id potentially
import { useOrg } from '@/contexts/OrgContext';

interface ItemFormData {
  name: string;
  description?: string;
  default_price?: number | string; // string for input, number for API
  default_unit?: string;
  image_url?: string; // This is where the image URL will be stored
}

interface ItemFormProps {
  mode: 'create' | 'edit';
  initialData?: Item; // Full Item object for editing
  organizationId: string; // Always required, for create and context (though activeOrg is also used)
  onSuccess: (processedItem: Item) => void;
  onCancel: () => void;
}

const ItemForm = ({ mode, initialData, organizationId, onSuccess, onCancel }: ItemFormProps) => {
  // activeOrganization is used to get the ID for creation if organizationId prop isn't explicitly used
  // but having organizationId prop is good for clarity if the form is ever used outside activeOrg context.
  const { activeOrganization } = useOrg(); 
  const [formData, setFormData] = useState<ItemFormData>({
    name: '',
    description: '',
    default_price: '',
    default_unit: '',
    image_url: '', // Initialized correctly
  });

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setFormData({
        name: initialData.name || '',
        description: initialData.description || '',
        default_price: initialData.default_price?.toString() || '', 
        default_unit: initialData.default_unit || '',
        image_url: initialData.image_url || '', // Populates from initialData
      });
    } else {
      // Reset for create mode or if initialData is not available for edit
      setFormData({ 
        name: '', 
        description: '', 
        default_price: '', 
        default_unit: '', 
        image_url: '' 
      });
    }
  }, [mode, initialData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    
    const orgIdForApi = mode === 'create' ? (organizationId || activeOrganization?.id) : undefined;

    if (mode === 'create' && !orgIdForApi) {
      setError("No active organization selected or organization ID provided.");
      return;
    }
    setIsLoading(true);
    setError(null);

    const priceString = String(formData.default_price).trim();
    const priceAsNumber = priceString === '' ? undefined : parseFloat(priceString);

    if (priceString !== '' && (priceAsNumber === undefined || isNaN(priceAsNumber) || priceAsNumber < 0)) {
         setError("Default price must be a valid positive number or empty.");
         setIsLoading(false);
         return;
    }

    const apiData = {
      name: formData.name,
      description: formData.description || undefined,
      default_price: priceAsNumber, // Will be number or undefined
      default_unit: formData.default_unit || undefined,
      image_url: formData.image_url || undefined, // Correctly included
      ...(mode === 'create' && orgIdForApi && { organization_id: orgIdForApi }),
    };
    
    // --- FRIEND'S DEBUGGING STEP ---
    console.log("Submitting Item API Data:", JSON.stringify(apiData, null, 2));
    // --- END DEBUGGING STEP ---

    try {
      let response;
      if (mode === 'edit' && initialData?.id) {
        response = await apiClient.put<Item>(`/items/${initialData.id}`, apiData);
      } else {
        response = await apiClient.post<Item>('/items/', apiData);
      }
      onSuccess(response.data);
    } catch (err: any) {
      console.error(`Failed to ${mode} item:`, err);
      setError(err.response?.data?.detail || `Failed to ${mode} item. ${err.message || ''}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="name">Item Name <span className="text-destructive">*</span></Label>
        <Input 
          id="name" 
          name="name" 
          value={formData.name} 
          onChange={handleChange} 
          required 
          disabled={isLoading} 
          className="mt-2" 
        />
      </div>
      <div>
        <Label htmlFor="description">Description</Label>
        <Textarea 
          id="description" 
          name="description" 
          value={formData.description || ''} 
          onChange={handleChange} 
          disabled={isLoading} 
          className="mt-2" 
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="default_price">Default Price</Label>
          <Input 
            id="default_price" 
            name="default_price" 
            type="number" 
            step="0.01" 
            min="0"
            value={formData.default_price || ''} 
            onChange={handleChange} 
            disabled={isLoading} 
            className="mt-2" 
            placeholder="e.g., 10.99"
          />
        </div>
        <div>
          <Label htmlFor="default_unit">Default Unit</Label>
          <Input 
            id="default_unit" 
            name="default_unit" 
            value={formData.default_unit || ''} 
            onChange={handleChange} 
            disabled={isLoading} 
            className="mt-2" 
            placeholder="e.g., piece, kg, hour"
          />
        </div>
      </div>
      <div>
        <Label htmlFor="image_url">Image URL (Optional)</Label>
        <Input 
          id="image_url" 
          name="image_url" 
          type="url" 
          value={formData.image_url || ''} 
          onChange={handleChange} 
          disabled={isLoading} 
          className="mt-2" 
          placeholder="https://example.com/image.png"
        />
      </div>

      {error && <p className="text-sm text-destructive text-center">{error}</p>}
      
      <div className="flex justify-end space-x-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>Cancel</Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? (mode === 'edit' ? 'Saving...' : 'Creating...') : (mode === 'edit' ? 'Save Changes' : 'Create Item')}
        </Button>
      </div>
    </form>
  );
};
export default ItemForm;