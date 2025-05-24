// src/pages/HomePage.tsx
import { useEffect, useState } from 'react';
import apiClient from '@/services/apiClient';
import { DashboardStats } from '@/types';
import { useOrg } from '@/contexts/OrgContext'; // To get activeOrganization for filtering
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker"; // Assuming this is your composite component
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TrendingUp, CircleDollarSign, AlertTriangle, CalendarDays } from "lucide-react"; // Example icons
import { format, subMonths, startOfMonth, endOfMonth, startOfYear, endOfYear } from 'date-fns'; // For date manipulation

type DateRangePreset = "all_time" | "this_month" | "last_month" | "this_year";

const HomePage = () => {
  const { activeOrganization } = useOrg();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Date filter state
  const [dateFrom, setDateFrom] = useState<Date | undefined>(undefined);
  const [dateTo, setDateTo] = useState<Date | undefined>(undefined);
  const [datePreset, setDatePreset] = useState<DateRangePreset>("all_time");

  const fetchDashboardStats = async (
     orgId?: string, 
     from?: Date, 
     to?: Date
 ) => {
    setIsLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (orgId) params.organization_id = orgId;
      if (from) params.date_from = format(from, 'yyyy-MM-dd');
      if (to) params.date_to = format(to, 'yyyy-MM-dd');
      
      const response = await apiClient.get<DashboardStats>('/dashboard/stats', { params });
      setStats(response.data);
    } catch (err: any) {
      console.error("Failed to fetch dashboard stats:", err);
      setError(err.response?.data?.detail || 'Failed to load dashboard statistics.');
      setStats(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Fetch stats when activeOrganization changes or date filters change
    if (activeOrganization || datePreset !== "all_time" || dateFrom || dateTo) {
         let effectiveFrom = dateFrom;
         let effectiveTo = dateTo;

         if (datePreset === "this_month") {
             effectiveFrom = startOfMonth(new Date());
             effectiveTo = endOfMonth(new Date());
         } else if (datePreset === "last_month") {
             const lastMonthStart = startOfMonth(subMonths(new Date(), 1));
             effectiveFrom = lastMonthStart;
             effectiveTo = endOfMonth(lastMonthStart);
         } else if (datePreset === "this_year") {
             effectiveFrom = startOfYear(new Date());
             effectiveTo = endOfYear(new Date());
         } else if (datePreset === "all_time") {
             // Clear custom dates if "all_time" is selected from preset
             // (but allow custom dates if preset is changed *away* from all_time)
             if(dateFrom || dateTo) { // If custom dates were set, keep them unless preset forces all_time
                 // This logic can be complex if presets and custom ranges interact.
                 // For simplicity, if preset is "all_time", nullify custom dates for API.
                 effectiveFrom = undefined;
                 effectiveTo = undefined;
             }
         }
         // If custom dates are set, they override presets (unless preset is "all_time")
         if (dateFrom && datePreset !== "all_time") effectiveFrom = dateFrom;
         if (dateTo && datePreset !== "all_time") effectiveTo = dateTo;

         fetchDashboardStats(activeOrganization?.id, effectiveFrom, effectiveTo);
    } else if (!activeOrganization) {
         // If no active organization and no date filters, maybe show global stats or a prompt
         // For now, let's just clear/don't fetch if no org is selected (unless we want user-wide stats)
         setStats(null); 
         setIsLoading(false); // Not loading if no org
    }
  }, [activeOrganization, dateFrom, dateTo, datePreset]);


  const handleDatePresetChange = (value: string) => {
     const preset = value as DateRangePreset;
     setDatePreset(preset);
     // When a preset is chosen, clear custom date range to avoid conflict
     // unless we want presets to just *set* the custom range.
     // For now, presets will override the dateFrom/dateTo sent to API.
     if (preset === "all_time") {
         setDateFrom(undefined);
         setDateTo(undefined);
     } else if (preset === "this_month") {
         setDateFrom(startOfMonth(new Date()));
         setDateTo(endOfMonth(new Date()));
     } else if (preset === "last_month") {
         const lastMonthStart = startOfMonth(subMonths(new Date(), 1));
         setDateFrom(lastMonthStart);
         setDateTo(endOfMonth(lastMonthStart));
     } else if (preset === "this_year") {
         setDateFrom(startOfYear(new Date()));
         setDateTo(endOfYear(new Date()));
     }
  };
  
  const currencySymbol = stats?.currency === "USD" ? "$" : stats?.currency === "AED" ? "AED" : (stats?.currency || "");

  if (!activeOrganization && !isLoading) { // Check isLoading to avoid showing this during initial org load
     return (
         <div className="text-center py-10">
             <p className="text-lg text-muted-foreground">Please select an organization to view its dashboard.</p>
             {/* Optionally link to organizations page */}
         </div>
     );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
        <h1 className="text-3xl font-bold">
          Dashboard {activeOrganization ? `for ${activeOrganization.name}` : ''}
        </h1>
        <div className="flex flex-wrap items-center gap-2 justify-start sm:justify-end"> 
            {/* `flex-wrap` allows items to wrap to the next line if not enough space */}
            {/* `justify-start sm:justify-end` to align them better within their available space */}
            <Select value={datePreset} onValueChange={handleDatePresetChange}>
                <SelectTrigger className="w-full sm:w-[180px]"> {/* Full width on small, fixed on sm+ */}
                    <SelectValue placeholder="Select date range" />
                </SelectTrigger>
                <SelectContent>
                     <SelectItem value="all_time">All Time</SelectItem>
                     <SelectItem value="this_month">This Month</SelectItem>
                     <SelectItem value="last_month">Last Month</SelectItem>
                     <SelectItem value="this_year">This Year</SelectItem>
                     {/* <SelectItem value="custom">Custom Range</SelectItem> */}
                 </SelectContent>
            </Select>
            <DatePicker date={dateFrom} onDateChange={setDateFrom} placeholder="From Date" className="w-full sm:w-auto" /> {/* Full width on small, auto on sm+ */}
            <DatePicker date={dateTo} onDateChange={setDateTo} placeholder="To Date" className="w-full sm:w-auto" />
        </div>
      </div>

      {isLoading && <div className="text-center py-10">Loading dashboard data...</div>}
      {error && <div className="text-center py-10 text-destructive">{error}</div>}

      {!isLoading && !error && stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Invoiced</CardTitle>
              <CircleDollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                 {currencySymbol} {stats.total_invoiced_amount.toFixed(2)}
              </div>
              {/* <p className="text-xs text-muted-foreground">+20.1% from last month</p> */}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Collected</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" /> {/* Placeholder icon */}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                 {currencySymbol} {stats.total_collected_amount.toFixed(2)}
              </div>
              {/* <p className="text-xs text-muted-foreground">+15% from last month</p> */}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Outstanding</CardTitle>
              <CircleDollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                 {currencySymbol} {stats.total_outstanding_amount.toFixed(2)}
              </div>
              {/* <p className="text-xs text-muted-foreground">outstanding balance</p> */}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Overdue Invoices</CardTitle>
              <AlertTriangle className="h-4 w-4 text-destructive" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.count_overdue_invoices}</div>
              {/* <p className="text-xs text-muted-foreground">count of overdue invoices</p> */}
            </CardContent>
          </Card>
        </div>
      )}
      {!isLoading && !error && !stats && !activeOrganization && (
         <div className="text-center py-10">
             <p className="text-lg text-muted-foreground">Select an organization to view dashboard statistics.</p>
         </div>
      )}
      {!isLoading && !error && !stats && activeOrganization && (
         <div className="text-center py-10">
             <p className="text-lg text-muted-foreground">No dashboard data available for the selected criteria.</p>
         </div>
      )}
    </div>
  );
};

export default HomePage;