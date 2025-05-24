
// src/components/invoices/RecordPaymentForm.tsx
import { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { DatePicker } from "@/components/ui/date-picker";
import apiClient from '@/services/apiClient';
import { Invoice, InvoiceSummary } from '@/types'; // Invoice for response, InvoiceSummary for input context
import { format } from 'date-fns';

interface RecordPaymentFormProps {
  invoice: InvoiceSummary; // To display info and use its ID
  onSuccess: (updatedInvoice: Invoice) => void;
  onCancel: () => void;
}

const RecordPaymentForm = ({ invoice, onSuccess, onCancel }: RecordPaymentFormProps) => {
  const [amountPaidNow, setAmountPaidNow] = useState<string>('');
  const [paymentDate, setPaymentDate] = useState<Date | undefined>(new Date());
  const [paymentMethod, setPaymentMethod] = useState<string>('');
  const [notes, setNotes] = useState<string>('');

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    const amount = parseFloat(amountPaidNow);
    if (isNaN(amount) || amount <= 0) {
      setError("Please enter a valid positive payment amount.");
      setIsLoading(false);
      return;
    }
    if (!paymentDate) {
      setError("Please select a payment date.");
      setIsLoading(false);
      return;
    }

    const payload = {
      amount_paid_now: amount,
      payment_date: format(paymentDate, 'yyyy-MM-dd'),
      payment_method: paymentMethod || undefined,
      notes: notes || undefined,
    };

    try {
      const response = await apiClient.post<Invoice>(`/invoices/${invoice.id}/record-payment`, payload);
      onSuccess(response.data);
    } catch (err: any) {
      console.error("Failed to record payment:", err);
      setError(err.response?.data?.detail || 'Failed to record payment.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 py-4">
      <div>
        <Label htmlFor="amountPaidNow">Payment Amount ({invoice.currency})</Label>
        <Input
          id="amountPaidNow"
          type="number"
          step="0.01"
          value={amountPaidNow}
          onChange={(e) => setAmountPaidNow(e.target.value)}
          className="mt-1"
          required
          disabled={isLoading}
          placeholder="0.00"
        />
      </div>
      <div>
        <Label htmlFor="paymentDate">Payment Date</Label>
        <DatePicker date={paymentDate} onDateChange={setPaymentDate} className="mt-1 w-full" disabled={isLoading}/>
      </div>
      <div>
        <Label htmlFor="paymentMethod">Payment Method (Optional)</Label>
        <Input
          id="paymentMethod"
          value={paymentMethod}
          onChange={(e) => setPaymentMethod(e.target.value)}
          className="mt-1"
          disabled={isLoading}
          placeholder="e.g., Bank Transfer, Cash"
        />
      </div>
      <div>
        <Label htmlFor="notes">Notes (Optional)</Label>
        <Textarea
          id="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="mt-1"
          rows={3}
          disabled={isLoading}
        />
      </div>

      {error && <p className="text-sm text-destructive text-center">{error}</p>}
      
      <div className="flex justify-end space-x-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Recording...' : 'Record Payment'}
        </Button>
      </div>
    </form>
  );
};

export default RecordPaymentForm;
