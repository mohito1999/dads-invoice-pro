// src/components/items/ItemForm.tsx
import { useState, useEffect, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import apiClient from '@/services/apiClient';
import { Item, ItemImage as ItemImageInterface } from '@/types'; // Renamed ItemImage to ItemImageInterface for clarity
import { getFullStaticUrl } from '@/config';
import { useOrg } from '@/contexts/OrgContext';
import { XCircleIcon, ImagePlusIcon, Trash2Icon } from "lucide-react"; // Use Trash2Icon for consistency
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"; // Import AlertDialog components

interface ItemFormData {
  name: string;
  description?: string;
  default_price?: string;
  default_unit?: string;
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
  });

  const [existingImages, setExistingImages] = useState<ItemImageInterface[]>([]);
  const [newImageFiles, setNewImageFiles] = useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false); 

  // State for image deletion dialog
  const [isDeleteImageDialogOpen, setIsDeleteImageDialogOpen] = useState(false);
  const [imageToDelete, setImageToDelete] = useState<ItemImageInterface | null>(null);
  const [isDeletingImage, setIsDeletingImage] = useState(false);


  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setFormData({
        name: initialData.name || '',
        description: initialData.description || '',
        default_price: initialData.default_price?.toString() || '',
        default_unit: initialData.default_unit || '',
      });
      setExistingImages(initialData.images || []);
      setNewImageFiles([]); 
      setImagePreviews([]);
    } else { 
      setFormData({ name: '', description: '', default_price: '', default_unit: '' });
      setExistingImages([]);
      setNewImageFiles([]);
      setImagePreviews([]);
    }
  }, [mode, initialData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
     if (event.target.files) {
         const filesArray = Array.from(event.target.files);
         setNewImageFiles(prevFiles => [...prevFiles, ...filesArray]);
         const newPreviews = filesArray.map(file => URL.createObjectURL(file));
         setImagePreviews(prevPreviews => [...prevPreviews, ...newPreviews]);
     }
  };

  const removeNewImage = (index: number) => {
     const removedPreview = imagePreviews[index];
     setNewImageFiles(prev => prev.filter((_, i) => i !== index));
     setImagePreviews(prev => prev.filter((_, i) => i !== index));
     URL.revokeObjectURL(removedPreview); 
  };

  // Opens the confirmation dialog
  const openDeleteImageConfirmDialog = (image: ItemImageInterface) => {
    setImageToDelete(image);
    setIsDeleteImageDialogOpen(true);
  };

  // Actual deletion logic, called from AlertDialog
  const confirmDeleteExistingImage = async () => {
     if (!imageToDelete || !initialData?.id) return;
     
     setIsDeletingImage(true);
     try {
         await apiClient.delete(`/items/images/${imageToDelete.id}`);
         setExistingImages(prev => prev.filter(img => img.id !== imageToDelete.id));
         toast.success("Image deleted successfully.");
     } catch (err: any) {
         console.error("Failed to delete image:", err);
         toast.error(err.response?.data?.detail || "Failed to delete image.");
     } finally {
         setIsDeletingImage(false);
         setIsDeleteImageDialogOpen(false);
         setImageToDelete(null);
     }
  };
  
  useEffect(() => {
     return () => {
         imagePreviews.forEach(url => URL.revokeObjectURL(url));
     };
  }, [imagePreviews]);


  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mode === 'create' && !activeOrganization?.id) {
      setError("No active organization selected.");
      return;
    }
    setIsSubmitting(true);
    setError(null);

    const priceAsNumber = formData.default_price ? parseFloat(String(formData.default_price)) : undefined;
     if (formData.default_price && (isNaN(priceAsNumber) || (priceAsNumber !== undefined && priceAsNumber < 0))) {
          setError("Default price must be a non-negative number.");
          setIsSubmitting(false);
          return;
     }

    const itemPayload = {
      name: formData.name,
      description: formData.description || undefined,
      default_price: priceAsNumber,
      default_unit: formData.default_unit || undefined,
      ...(mode === 'create' && activeOrganization?.id && { organization_id: activeOrganization.id }),
    };
    
    try {
      let savedItem: Item;
      if (mode === 'edit' && initialData?.id) {
        const response = await apiClient.put<Item>(`/items/${initialData.id}`, itemPayload);
        savedItem = response.data;
      } else {
        const response = await apiClient.post<Item>('/items/', itemPayload);
        savedItem = response.data;
      }

      if (newImageFiles.length > 0) {
        setIsSubmitting(true); // Keep isSubmitting true or use a separate isUploading state
        const imageFormData = new FormData();
        newImageFiles.forEach(file => {
          imageFormData.append('files', file);
        });
        
        const imageUploadResponse = await apiClient.post<Item>(`/items/${savedItem.id}/images`, imageFormData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        savedItem = imageUploadResponse.data; 
      }
      
      toast.success(`Item "${savedItem.name}" ${mode === 'create' ? 'created' : 'updated'} successfully!`);
      onSuccess(savedItem);

    } catch (err: any) {
      console.error(`Failed to ${mode} item:`, err);
      const errMsg = err.response?.data?.detail || `Failed to ${mode} item.`;
      setError(errMsg);
      toast.error(errMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
           <Label htmlFor="name">Item Name</Label>
           <Input id="name" name="name" value={formData.name} onChange={handleChange} required disabled={isSubmitting} className="mt-1" />
        </div>
        <div>
           <Label htmlFor="description">Description</Label>
           <Textarea id="description" name="description" value={formData.description} onChange={handleChange} disabled={isSubmitting} className="mt-1" />
        </div>
        <div>
           <Label htmlFor="default_price">Default Price</Label>
           <Input id="default_price" name="default_price" type="number" step="0.01" min="0" value={formData.default_price} onChange={handleChange} disabled={isSubmitting} className="mt-1" />
        </div>
        <div>
           <Label htmlFor="default_unit">Default Unit (e.g., piece, kg)</Label>
           <Input id="default_unit" name="default_unit" value={formData.default_unit} onChange={handleChange} disabled={isSubmitting} className="mt-1" />
        </div>

        <div className="space-y-2">
           <Label>Images</Label>
           {existingImages.length > 0 && (
               <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2 mb-4">
                   {existingImages.map((img) => (
                       <div key={img.id} className="relative group border rounded-md p-1">
                           <img src={getFullStaticUrl(img.image_url)} alt={img.alt_text || `Item image ${img.order_index + 1}`} className="w-full h-24 object-cover rounded" />
                           <Button
                               type="button"
                               variant="destructive"
                               size="icon"
                               className="absolute top-1 right-1 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity z-10"
                               onClick={() => openDeleteImageConfirmDialog(img)} // Open dialog
                               disabled={isSubmitting || isDeletingImage}
                           >
                               <Trash2Icon className="h-3.5 w-3.5" />
                           </Button>
                       </div>
                   ))}
               </div>
           )}

           {imagePreviews.length > 0 && (
               <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2 mb-2">
                   {imagePreviews.map((previewUrl, index) => (
                       <div key={previewUrl} className="relative group border rounded-md p-1">
                           <img src={previewUrl} alt={`New image preview ${index + 1}`} className="w-full h-24 object-cover rounded" />
                           <Button
                               type="button"
                               variant="destructive"
                               size="icon"
                               className="absolute top-1 right-1 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity z-10"
                               onClick={() => removeNewImage(index)}
                               disabled={isSubmitting}
                           >
                               <XCircleIcon className="h-4 w-4" />
                           </Button>
                       </div>
                   ))}
               </div>
           )}

           <Input
               id="imageFiles"
               name="imageFiles"
               type="file"
               multiple
               accept="image/png, image/jpeg, image/gif, image/webp"
               onChange={handleFileChange}
               className="hidden" 
               ref={fileInputRef}
               disabled={isSubmitting}
           />
           <Button 
               type="button" 
               variant="outline" 
               onClick={() => fileInputRef.current?.click()}
               disabled={isSubmitting}
               className="w-full"
           >
               <ImagePlusIcon className="mr-2 h-4 w-4" /> Add Images
           </Button>
        </div>

        {error && <p className="text-sm text-destructive text-center">{error}</p>}
        
        <div className="flex justify-end space-x-3 pt-6">
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>Cancel</Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? (mode === 'edit' ? 'Saving...' : 'Creating...') : (mode === 'edit' ? 'Save Changes' : 'Create Item')}
          </Button>
        </div>
      </form>

      {/* AlertDialog for Deleting Existing Image */}
      <AlertDialog open={isDeleteImageDialogOpen} onOpenChange={setIsDeleteImageDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure you want to delete this image?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The image will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {setImageToDelete(null); setIsDeleteImageDialogOpen(false);}} disabled={isDeletingImage}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
                onClick={confirmDeleteExistingImage} 
                disabled={isDeletingImage}
                className="bg-destructive hover:bg-destructive/90 text-white"
            >
              {isDeletingImage ? "Deleting..." : "Yes, delete image"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};
export default ItemForm;