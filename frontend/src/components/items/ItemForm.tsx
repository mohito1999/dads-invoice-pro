// src/components/items/ItemForm.tsx
import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea"; // npx shadcn@latest add textarea
import apiClient from '@/services/apiClient';
import { Item } from '@/types';
import { useOrg } from '@/contexts/OrgContext';

interface ItemFormData {
  name: string;
  description?: string;
  default_price?: number | string; // string for input, number for API
  default_unit?: string;
  image_url?: string;
}

interface ItemFormProps {
  mode: 'create' | 'edit';
  initialData?: Item;
  onSuccess: (processedItem: Item) => void;
  onCancel: () => void;
}

const ItemForm = ({ mode, initialData, onSuccess, onCancel }: ItemFormProps) => {
  const { activeOrganization } = useOrg();
  const [formData, setFormData] = useState<ItemFormData>({
    name: '',
    description: '',
    default_price: '',
    default_unit: '',
    image_url: '',
  });

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setFormData({
        name: initialData.name || '',
        description: initialData.description || '',
        default_price: initialData.default_price?.toString() || '', // Convert number to string for input
        default_unit: initialData.default_unit || '',
        image_url: initialData.image_url || '',
      });
    } else {
      setFormData({ name: '', description: '', default_price: '', default_unit: '', image_url: '' });
    }
  }, [mode, initialData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mode === 'create' && !activeOrganization?.id) {
      setError("No active organization selected.");
      return;
    }
    setIsLoading(true);
    setError(null);

    const priceAsNumber = formData.default_price ? parseFloat(String(formData.default_price)) : undefined;
    if (formData.default_price && (isNaN(priceAsNumber) || (priceAsNumber !== undefined && priceAsNumber <= 0))) {
         setError("Default price must be a positive number.");
         setIsLoading(false);
         return;
    }


    const apiData = {
      name: formData.name,
      description: formData.description || undefined,
      default_price: priceAsNumber,
      default_unit: formData.default_unit || undefined,
      image_url: formData.image_url || undefined,
      ...(mode === 'create' && activeOrganization?.id && { organization_id: activeOrganization.id }),
    };
    
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
      setError(err.response?.data?.detail || `Failed to ${mode} item.`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="name">Item Name</Label>
        <Input id="name" name="name" value={formData.name} onChange={handleChange} required disabled={isLoading} className="mt-1" />
      </div>
      <div>
        <Label htmlFor="description">Description</Label>
        <Textarea id="description" name="description" value={formData.description} onChange={handleChange} disabled={isLoading} className="mt-1" />
      </div>
      <div>
        <Label htmlFor="default_price">Default Price</Label>
        <Input id="default_price" name="default_price" type="number" step="0.01" value={formData.default_price} onChange={handleChange} disabled={isLoading} className="mt-1" />
      </div>
      <div>
        <Label htmlFor="default_unit">Default Unit (e.g., piece, kg, hour)</Label>
        <Input id="default_unit" name="default_unit" value={formData.default_unit} onChange={handleChange} disabled={isLoading} className="mt-1" />
      </div>
      <div>
        <Label htmlFor="image_url">Image URL</Label>
        <Input id="image_url" name="image_url" type="url" value={formData.image_url} onChange={handleChange} disabled={isLoading} className="mt-1" placeholder="https://example.com/image.png"/>
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