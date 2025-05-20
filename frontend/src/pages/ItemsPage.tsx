// src/pages/ItemsPage.tsx
import { useEffect, useState } from 'react';
import apiClient from '@/services/apiClient';
import { Item, ItemSummary } from '@/types';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"; // DialogTrigger is implicit
import ItemForm from '@/components/items/ItemForm';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { MoreHorizontal, PlusCircle, Edit2Icon, Trash2Icon, ImageOff } from "lucide-react";
import { useOrg } from '@/contexts/OrgContext';
import { Link } from 'react-router-dom';
import { Input } from '@/components/ui/input';

const ItemsPage = () => {
  const { activeOrganization, isLoadingOrgs: isLoadingActiveOrg } = useOrg();
  const [items, setItems] = useState<ItemSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false); // For fetching items list
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [currentItem, setCurrentItem] = useState<Item | undefined>(undefined);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<ItemSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false); // Specific loading state for delete

  const fetchItems = async (orgId: string, search: string = "") => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ organization_id: orgId, skip: "0", limit: "1000" }); // Increased limit
      if (search) {
        params.append("search", search);
      }
      const response = await apiClient.get<ItemSummary[]>(`/items/?${params.toString()}`);
      setItems(response.data);
    } catch (err: any) {
      console.error("Failed to fetch items:", err);
      setError(err.response?.data?.detail || 'Failed to load items.');
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (activeOrganization?.id) {
      fetchItems(activeOrganization.id, searchTerm);
    } else if (!isLoadingActiveOrg) {
      setItems([]);
      setError(null); // Clear errors if no org is active
    }
  }, [activeOrganization, isLoadingActiveOrg, searchTerm]);

  const handleOpenCreateModal = () => {
    setFormMode('create'); 
    setCurrentItem(undefined); 
    setIsFormModalOpen(true);
  };

  const handleOpenEditModal = async (itemId: string) => {
    setFormMode('edit'); 
    try {
        const response = await apiClient.get<Item>(`/items/${itemId}`);
        setCurrentItem(response.data); 
        setIsFormModalOpen(true);
    } catch (err: any) { 
        alert(err.response?.data?.detail || "Failed to load item details."); 
    }
  };

  const handleFormSuccess = (processedItem: Item) => {
    if (activeOrganization?.id) fetchItems(activeOrganization.id, searchTerm);
    setIsFormModalOpen(false);
    alert(`Item "${processedItem.name}" ${formMode === 'create' ? 'created' : 'updated'} successfully!`);
  };

  const openDeleteConfirmDialog = (item: ItemSummary) => {
    setItemToDelete(item); 
    setIsDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!itemToDelete || !activeOrganization?.id) return;
    setIsDeleting(true);
    setError(null);
    try {
        await apiClient.delete(`/items/${itemToDelete.id}`);
        setItems(prevItems => prevItems.filter(i => i.id !== itemToDelete.id)); // Optimistic update
        alert(`Item "${itemToDelete.name}" deleted successfully.`);
    } catch (err:any) { 
        setError(err.response?.data?.detail || "Failed to delete item.");
        alert(err.response?.data?.detail || "Failed to delete item.");
    }
    finally { 
        setIsDeleting(false);
        setIsDeleteDialogOpen(false); 
        setItemToDelete(null); 
    }
  };

  if (isLoadingActiveOrg) {
    return <div className="container mx-auto px-4 py-10 text-center">Loading organization context...</div>;
  }

  if (!activeOrganization) {
    return (
      <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        <div className="flex justify-between items-center">
            <h1 className="text-2xl sm:text-3xl font-bold">Items</h1>
        </div>
        <Card className="w-full">
            <CardHeader>
                <CardTitle>No Active Organization</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="text-center py-10">
                    <p className="text-muted-foreground">Please select or create an active organization to manage items.</p>
                    <Button asChild className="mt-4">
                    <Link to="/organizations">Go to Organizations</Link>
                    </Button>
                </div>
            </CardContent>
        </Card>
      </div>
    );
  }
  
  // Initial loading state for items specific to the active organization
  if (isLoading && items.length === 0 && !searchTerm && !error) {
     return (
        <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <h1 className="text-2xl sm:text-3xl font-bold">Items for {activeOrganization.name}</h1>
                {/* Search and Create button can be here but might be better to show them with the card */}
            </div>
            <Card className="w-full">
                <CardHeader />
                <CardContent>
                    <div className="text-center py-10">Loading items...</div>
                </CardContent>
            </Card>
        </div>
     );
  }

  return (
    <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-2xl sm:text-3xl font-bold">Items for {activeOrganization.name}</h1>
        <div className="flex gap-2 w-full sm:w-auto">
          <Input 
             type="search" 
             placeholder="Search items..." 
             className="w-full sm:w-64"
             value={searchTerm}
             onChange={(e) => setSearchTerm(e.target.value)}
          />
          <Button onClick={handleOpenCreateModal} className="whitespace-nowrap">
            <PlusCircle className="mr-2 h-4 w-4" /> Create Item
          </Button>
        </div>
      </div>

      <Dialog open={isFormModalOpen} onOpenChange={setIsFormModalOpen}>
        <DialogContent className="sm:max-w-[525px]">
          <DialogHeader>
            <DialogTitle>{formMode === 'create' ? 'Create New Item' : 'Edit Item'}</DialogTitle>
            <DialogDescription>
              {formMode === 'create' ? `Adding item to organization: ${activeOrganization.name}.` : `Editing item: ${currentItem?.name || ''}`}
            </DialogDescription>
          </DialogHeader>
          {isFormModalOpen && (formMode === 'create' || (formMode === 'edit' && currentItem)) && (
            <ItemForm 
                mode={formMode} 
                initialData={currentItem} 
                organizationId={activeOrganization.id} // Pass active org ID
                onSuccess={handleFormSuccess} 
                onCancel={() => setIsFormModalOpen(false)} 
            />
          )}
        </DialogContent>
      </Dialog>

      <Card className="w-full">
        <CardHeader>
            {/* Optional CardTitle if needed, page title might be sufficient */}
            {/* <CardTitle>Product/Service Catalog</CardTitle> */}
             {error && items.length > 0 && ( // Show error as a notice if data is already present
                <p className="text-sm text-destructive py-2 px-1 text-center">{error}</p>
            )}
        </CardHeader>
        <CardContent className={(items.length === 0 || error) && !isLoading ? "pt-6" : ""}>
            {error && items.length === 0 && ( // Prominent error if list is empty due to error
                 <div className="text-center py-10 text-destructive">{error}</div>
            )}
            {!isLoading && items.length === 0 && !error ? (
                <div className="text-center py-10 border-2 border-dashed border-muted rounded-lg">
                    <h3 className="text-xl font-semibold mb-2">No Items Found</h3>
                    <p className="text-muted-foreground mb-4">
                        {searchTerm 
                            ? `No items found matching "${searchTerm}" in ${activeOrganization.name}.`
                            : `No items found for ${activeOrganization.name}. Add your first one!`}
                    </p>
                    <Button onClick={handleOpenCreateModal} size="lg">
                        <PlusCircle className="mr-2 h-5 w-5" /> Create Item
                    </Button>
                </div>
            ) : (
                !error && items.length > 0 && ( // Only show table if no error and items exist
                    <div className="rounded-md border">
                        <Table>
                        <TableHeader>
                            <TableRow>
                            <TableHead className="w-[60px] sm:w-[80px]">Image</TableHead>
                            <TableHead>Name</TableHead>
                            <TableHead className="hidden sm:table-cell">Description</TableHead>
                            <TableHead className="hidden md:table-cell">Default Price</TableHead>
                            <TableHead className="hidden md:table-cell">Default Unit</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {items.map((item) => (
                            <TableRow key={item.id}>
                                <TableCell>
                                {item.image_url ? (
                                    <img src={item.image_url} alt={item.name} className="h-10 w-10 sm:h-12 sm:w-12 object-cover rounded-md" />
                                ) : (
                                    <div className="h-10 w-10 sm:h-12 sm:w-12 bg-muted rounded-md flex items-center justify-center text-muted-foreground">
                                    <ImageOff className="h-5 w-5 sm:h-6 sm:w-6" />
                                    </div>
                                )}
                                </TableCell>
                                <TableCell className="font-medium">{item.name}</TableCell>
                                <TableCell className="hidden sm:table-cell text-sm text-muted-foreground max-w-xs truncate">
                                    {item.description || 'N/A'}
                                </TableCell>
                                <TableCell className="hidden md:table-cell">
                                    {item.default_price != null ? `$${item.default_price.toFixed(2)}` : 'N/A'}
                                </TableCell>
                                <TableCell className="hidden md:table-cell">{item.default_unit || 'N/A'}</TableCell>
                                <TableCell className="text-right">
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild><Button variant="ghost" className="h-8 w-8 p-0"><MoreHorizontal className="h-4 w-4" /></Button></DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                    <DropdownMenuItem onClick={() => handleOpenEditModal(item.id)} className="cursor-pointer"><Edit2Icon className="mr-2 h-4 w-4" />Edit</DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => openDeleteConfirmDialog(item)} className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer"><Trash2Icon className="mr-2 h-4 w-4" />Delete</DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                                </TableCell>
                            </TableRow>
                            ))}
                        </TableBody>
                        </Table>
                    </div>
                )
            )}
            {isLoading && (items.length > 0 || searchTerm) && ( // Loading indicator for refreshes or search loading
                <div className="text-center py-4 text-sm text-muted-foreground">Loading items...</div>
            )}
        </CardContent>
      </Card>

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the item "<strong>{itemToDelete?.name || ''}</strong>". This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {setItemToDelete(null); setIsDeleteDialogOpen(false);}}>Cancel</AlertDialogCancel>
            <AlertDialogAction 
                onClick={handleConfirmDelete} 
                disabled={isDeleting}
                className="bg-destructive hover:bg-destructive/90 text-destructive-foreground"
            >
              {isDeleting ? "Deleting..." : "Yes, delete item"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default ItemsPage;