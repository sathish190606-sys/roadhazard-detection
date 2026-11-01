import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, MapPin, Loader2, X, Navigation2 } from 'lucide-react';

interface NominatimResult {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
  type: string;
  class: string;
  address?: {
    road?: string;
    suburb?: string;
    city?: string;
    state?: string;
    country?: string;
  };
}

interface LocationSearchProps {
  onLocationSelect: (lat: number, lng: number, label: string) => void;
}

export const LocationSearch: React.FC<LocationSearchProps> = ({ onLocationSelect }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<NominatimResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setIsFocused(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const searchLocation = useCallback(async (searchQuery: string) => {
    if (searchQuery.trim().length < 3) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    setIsLoading(true);

    try {
      const params = new URLSearchParams({
        q: searchQuery,
        format: 'json',
        addressdetails: '1',
        limit: '6',
      });

      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?${params.toString()}`,
        {
          signal: controller.signal,
          headers: { 'Accept-Language': 'en' },
        }
      );

      if (!res.ok) throw new Error('Search failed');
      const data: NominatimResult[] = await res.json();
      setResults(data);
      setIsOpen(data.length > 0);
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('[LocationSearch] Error:', err);
        setResults([]);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounced search – fires 400ms after user stops typing
  useEffect(() => {
    if (selectedLabel) return; // Don't re-search after a selection

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      searchLocation(query);
    }, 400);

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, [query, searchLocation, selectedLabel]);

  const handleSelect = (result: NominatimResult) => {
    const lat = parseFloat(result.lat);
    const lng = parseFloat(result.lon);
    const shortLabel = formatShortLabel(result);
    setQuery(shortLabel);
    setSelectedLabel(shortLabel);
    setIsOpen(false);
    setResults([]);
    onLocationSelect(lat, lng, result.display_name);
  };

  const handleClear = () => {
    setQuery('');
    setSelectedLabel(null);
    setResults([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    setSelectedLabel(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      inputRef.current?.blur();
    }
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-xs" style={{ zIndex: 600 }}>
      {/* Search Input */}
      <div
        className={`flex items-center gap-2 rounded-xl px-3 py-2 backdrop-blur-xl shadow-xl border transition-all duration-300 ${
          isFocused
            ? 'bg-slate-900/95 border-cyan-500/50 ring-2 ring-cyan-500/20 shadow-cyan-500/10'
            : 'bg-slate-950/90 border-slate-700/60 hover:border-slate-600'
        }`}
      >
        <div className="flex-shrink-0">
          {isLoading ? (
            <Loader2 className="h-4 w-4 text-cyan-400 animate-spin" />
          ) : (
            <Search className={`h-4 w-4 transition-colors ${isFocused ? 'text-cyan-400' : 'text-slate-500'}`} />
          )}
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onFocus={() => {
            setIsFocused(true);
            if (results.length > 0) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Search location..."
          className="flex-1 bg-transparent text-xs text-white placeholder-slate-500 outline-none min-w-0"
          autoComplete="off"
          spellCheck={false}
        />
        {query.length > 0 && (
          <button
            onClick={handleClear}
            className="flex-shrink-0 rounded-md p-0.5 text-slate-500 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Results Dropdown */}
      {isOpen && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1.5 rounded-xl bg-slate-950/95 border border-slate-700/60 backdrop-blur-xl shadow-2xl overflow-hidden animate-in">
          <div className="px-3 py-1.5 border-b border-slate-800/50">
            <span className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold">
              {results.length} location{results.length !== 1 ? 's' : ''} found
            </span>
          </div>
          <ul className="max-h-60 overflow-y-auto py-1">
            {results.map((result) => (
              <li key={result.place_id}>
                <button
                  onClick={() => handleSelect(result)}
                  className="w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-cyan-500/10 transition-colors group"
                >
                  <div className="flex-shrink-0 mt-0.5 rounded-lg bg-slate-800 group-hover:bg-cyan-500/20 p-1.5 transition-colors">
                    <MapPin className="h-3 w-3 text-slate-400 group-hover:text-cyan-400 transition-colors" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-slate-200 group-hover:text-white truncate transition-colors">
                      {formatShortLabel(result)}
                    </div>
                    <div className="text-[10px] text-slate-500 truncate mt-0.5">
                      {result.display_name}
                    </div>
                    <div className="text-[10px] font-mono text-slate-600 mt-0.5">
                      {parseFloat(result.lat).toFixed(5)}, {parseFloat(result.lon).toFixed(5)}
                    </div>
                  </div>
                  <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity mt-1">
                    <Navigation2 className="h-3 w-3 text-cyan-400" />
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* No results message */}
      {isOpen && results.length === 0 && query.length >= 3 && !isLoading && (
        <div className="absolute top-full left-0 right-0 mt-1.5 rounded-xl bg-slate-950/95 border border-slate-700/60 backdrop-blur-xl shadow-2xl p-4 text-center">
          <Search className="h-5 w-5 text-slate-600 mx-auto mb-1.5" />
          <p className="text-[11px] text-slate-500">No locations found for "{query}"</p>
          <p className="text-[10px] text-slate-600 mt-0.5">Try a different search term</p>
        </div>
      )}
    </div>
  );
};

/**
 * Format a Nominatim result into a short, readable label.
 * Falls back to the full display_name if no address parts are available.
 */
function formatShortLabel(result: NominatimResult): string {
  const addr = result.address;
  if (!addr) return result.display_name.split(',').slice(0, 2).join(', ');

  const parts: string[] = [];
  if (addr.road) parts.push(addr.road);
  if (addr.suburb) parts.push(addr.suburb);
  if (addr.city) parts.push(addr.city);

  if (parts.length === 0) {
    return result.display_name.split(',').slice(0, 2).join(', ');
  }
  return parts.join(', ');
}
