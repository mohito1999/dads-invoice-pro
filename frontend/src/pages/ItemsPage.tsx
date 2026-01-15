// src/pages/ItemsPage.tsx
import { useEffect, useState } from 'react';
import apiClient from '@/services/apiClient';
import { Item, ItemSummary } from '@/types'; // Item is for full item details for form
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import ItemForm from '@/components/items/ItemForm';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { MoreHorizontal, PlusCircle, Edit2Icon, Trash2Icon, ImageIcon } from "lucide-react";
import { useOrg } from '@/contexts/OrgContext';
import { Link } from 'react-router-dom';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { getFullStaticUrl } from '@/config';

const ItemsPage = () => {
  const { activeOrganization, isLoadingOrgs: isLoadingActiveOrg } = useOrg();
  const [items, setItems] = useState<ItemSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [currentItem, setCurrentItem] = useState<Item | undefined>(undefined);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<ItemSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const getErrorMessage = (err: any): string => {
    if (err.response?.data?.detail) {
      const detail = err.response.data.detail;
      if (Array.isArray(detail) && detail.length > 0 && typeof detail[0].msg === 'string') {
        // Handle FastAPI validation error array
        return detail.map((e: any) => `${e.loc.join('.')} - ${e.msg}`).join('; ');
      } else if (typeof detail === 'string') {
        return detail;
      }
    }
    return err.message || 'An unknown error occurred.';
  };

  const fetchItems = async (orgId: string, search: string = "") => {
    setIsLoading(true);
    setError(null);
    try {
      // FIX 1: Changed limit to 100 (or any value <= 200 as per backend)
      const params = new URLSearchParams({ organization_id: orgId, skip: "0", limit: "100" });
      if (search) {
        params.append("search", search);
      }
      const response = await apiClient.get<ItemSummary[]>(`/items/?${params.toString()}`);
      setItems(response.data);
    } catch (err: any) {
      console.error("Failed to fetch items:", err);
      // FIX 2: Ensure error message is a string
      setError(getErrorMessage(err));
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
      setError(null);
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
      toast.error(getErrorMessage(err) || "Failed to load item details for editing.");
    }
  };

  const handleFormSuccess = (processedItem: Item) => {
    if (activeOrganization?.id) {
      fetchItems(activeOrganization.id, searchTerm);
    }
    setIsFormModalOpen(false);
    toast.success(`Item "${processedItem.name}" ${formMode === 'create' ? 'created' : 'updated'} successfully!`);
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
      fetchItems(activeOrganization.id, searchTerm);
      toast.success(`Item "${itemToDelete.name}" deleted successfully.`);
    } catch (err: any) {
      const errMsg = getErrorMessage(err);
      setError(errMsg);
      toast.error(errMsg || "Failed to delete item.");
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

  if (isLoading && items.length === 0 && !searchTerm && !error) {
    return (
      <div className="container mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <h1 className="text-2xl sm:text-3xl font-bold">Items for {activeOrganization.name}</h1>
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
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{formMode === 'create' ? 'Create New Item' : `Edit Item: ${currentItem?.name || ''}`}</DialogTitle>
            {formMode === 'create' &&
              <DialogDescription>
                Adding a new item to organization: {activeOrganization.name}.
              </DialogDescription>
            }
          </DialogHeader>
          {isFormModalOpen && (formMode === 'create' || (formMode === 'edit' && currentItem)) && (
            <ItemForm
              mode={formMode}
              initialData={formMode === 'edit' ? currentItem : undefined}
              onSuccess={handleFormSuccess}
              onCancel={() => setIsFormModalOpen(false)}
            />
          )}
        </DialogContent>
      </Dialog>

      <Card className="w-full">
        <CardHeader>
          {error && items.length > 0 && (
            <p className="text-sm text-destructive py-2 px-1 text-center">{error}</p>
          )}
        </CardHeader>
        <CardContent className={(items.length === 0 || error) && !isLoading ? "pt-6" : ""}>
          {error && items.length === 0 && (
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
            !error && items.length > 0 && (
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[60px]">Image</TableHead>
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
                            <img
                              src={getFullStaticUrl(item.image_url)}
                              alt={item.name}
                              className="h-10 w-10 object-contain rounded-sm"
                            />
                          ) : (
                            <div className="h-10 w-10 bg-muted rounded-sm flex items-center justify-center text-muted-foreground">
                              <ImageIcon className="h-5 w-5" />
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
          {isLoading && (items.length > 0 || searchTerm) && (
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
            <AlertDialogCancel onClick={() => { setItemToDelete(null); setIsDeleteDialogOpen(false); }}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={isDeleting}
              className="bg-destructive hover:bg-destructive/90 text-white"
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