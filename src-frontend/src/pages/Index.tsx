import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Calendar,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Search,
} from "lucide-react";
import { useState, useEffect } from "react";
import { json } from "stream/consumers";

declare interface apiReturn {
  id: number;
  title: string;
  description: string;
  image_url: string;
  reporter: string;
  language: string;
  region: string;
  category: string;
  date: string;
}

const Index = () => {
  const [newsData, setNewsData] = useState<apiReturn[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [searchResults, setSearchResults] = useState<apiReturn[] | null>(null);
  const [searchLoading, setSearchLoading] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [expandedArticles, setExpandedArticles] = useState<Set<number>>(new Set());
  const [selectedCategory, setSelectedCategory] = useState<string>("All News");
  const [expandable, setExpandable] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Toggle whether an article is expanded.
  const toggleArticle = (id: number) => {
    setExpandedArticles((prev) => {
      const copy = new Set(prev);
      if (copy.has(id)) copy.delete(id);
      else copy.add(id);
      return copy;
    });
  };

  // Updated list of all categories (matching backend enum)
  const categories = [
    "All News",
    "World",
    "Interviews",
    "Opinion",
    "Articles",
    "Sports",
    "Editorials",
    "Other",
  ];
  const BASE_URL = "http://localhost:3000"
  // Initial load: fetch recent news (by language "EN")
  useEffect(() => {
    fetch(`${BASE_URL}/api/recent/EN`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.clone().json() as Promise<apiReturn[]>;
      })
      .then((jsonArray) => {
        console.log("invalid json",jsonArray)
        setNewsData(jsonArray);
      })

      .finally(() => {
        setLoading(false);
      });
  }, []);

  // Handle Enter key in search input.
  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && searchQuery.trim().length > 0) {
      performSearch(searchQuery.trim());
    }
  };

  // Perform search via /api/search/all/{term}
  const performSearch = async (term: string) => {
    setSearchLoading(true);
    setSearchError(null);
    setSearchResults(null);

    try {
      const res = await fetch(`${BASE_URL}/api/search/all/${encodeURIComponent(term)}`);
      if (!res.ok) {
        throw new Error(`Search HTTP ${res.status}`);
      }
      const results = (await res.json()) as apiReturn[];
      setSearchResults(results);
    } catch (e) {
      console.error("Search failed:", e);
      setSearchError("Search failed. Please try again.");
    } finally {
      setSearchLoading(false);
    }
  };

  // Clear search results when query is emptied
  useEffect(() => {
    if (searchQuery.trim().length === 0) {
      setSearchResults(null);
      setSearchError(null);
    }
  }, [searchQuery]);

  // Filter by category (only when not searching)
  const filteredByCategory =
    selectedCategory === "All News"
      ? newsData
      : newsData.filter((n) => n.category === selectedCategory);

  // Determine which list to show: searchResults (if not null) else category-filtered
  const newsToShow = searchResults !== null ? searchResults : filteredByCategory;

  const isAnyLoading = loading || searchLoading;
  const anyError = error || searchError;

  return (
    <div className="min-h-screen bg-[#0F254D] text-[#E5E7EB]">
      {/* Header */}
      <header className="bg-[#0F254D] border-b border-[#0A1C3B]">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          {/* Logo on the Left */}
          <div className="flex items-center space-x-3">
            <img
              src="/logo"
              alt="EarthMC Live"
              className="h-12 w-13 object-contain"
            />
          </div>

          {/* Search Bar on Top Right */}
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#7E7E85] w-4 h-4" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              className="w-full bg-[#0F254D] border border-[#0A1C3B] text-[#E5E7EB] placeholder-[#7E7E85] pl-10 pr-3 py-1 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-800"
            />
          </div>
        </div>
      </header>

      {/* Category Navigation (hidden during active search) */}
      {searchResults === null && (
        <nav className="bg-[#0F254D] select-none">
          <div className="container mx-auto px-4">
            <div className="flex space-x-2 py-3 overflow-x-auto">
              {categories.map((category) => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`px-4 py-1 rounded-md text-sm font-medium transition-colors duration-150 ${
                    selectedCategory === category
                      ? "bg-green-800 text-[#E5E7EB]"
                      : "bg-[#0F254D] text-[#F3F4F6] hover:bg-green-800 hover:text-[#E5E7EB]"
                  }`}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>
        </nav>
      )}

      <main className="container mx-auto px-4 py-6">
        {/* Section Title */}
        <h2 className="text-2xl font-semibold mb-6 text-center text-[#E5E7EB]">
          {searchResults !== null
            ? `Search Results for “${searchQuery}”`
            : selectedCategory === "All News"
            ? "Latest News & Updates"
            : selectedCategory}
        </h2>

        {isAnyLoading && (
          <p className="text-center text-[#7E7E85]">Loading...</p>
        )}
        {anyError && (
          <p className="text-center text-red-500">{anyError}</p>
        )}

        {/* News Grid */}
        {!isAnyLoading && !anyError && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {newsToShow.map((article) => {
              const isExpanded = expandedArticles.has(article.id);

              return (
                <Card
                  key={article.id}
                  className="bg-[#162F61] text-white border border-[#0A1C3B] hover:border-green-800 transition-colors duration-150"
                >
                  {/* Image */}
                  <div className="h-40 overflow-hidden rounded-t-md">
                    <img
                      src={article.image_url}
                      alt={article.title}
                      className="object-cover w-full h-full opacity-80"
                    />
                  </div>

                  <CardHeader className="p-3 bg-[#1E3564]">
                    {/* Category, Region & Date */}
                    <div className="flex items-center justify-between mb-1 space-x-2">
                      <Badge
                        variant="secondary"
                        className="bg-green-800 text-white text-xs py-0.5 px-2 rounded"
                      >
                        {article.category}
                      </Badge>
                      <Badge
                        variant="secondary"
                        className="bg-[#3E5A86] text-white text-xs py-0.5 px-2 rounded"
                      >
                        {article.region}
                      </Badge>
                      <div className="flex items-center text-xs text-white ml-auto">
                        <Calendar className="h-3 w-3 mr-0.5 text-white" />
                        {article.date}
                      </div>
                    </div>

                    {/* Title */}
                    <CardTitle className="text-base font-medium hover:text-green-600 cursor-pointer text-white">
                      {article.title}
                    </CardTitle>

                    {/* Description */}
                    <p
                      ref={(el) => {
                        if (!el) return;
                        const isOverflowing = el.scrollHeight > el.clientHeight;
                        const alreadyHasOverflow = el.dataset.overflow === "true";
                        if (isOverflowing && !alreadyHasOverflow) {
                          el.dataset.overflow = "true";
                          setExpandable((prev) => new Set(prev.add(article.id)));
                        }
                      }}
                      className={`mt-1 text-sm text-white transition-all duration-150 ${
                        isExpanded ? "line-clamp-none" : "line-clamp-3"
                      }`}
                    >
                      {article.description}
                    </p>
                  </CardHeader>

                  <CardContent className="p-3 pt-1 bg-[#1E3564]">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-white">
                        By {article.reporter} &nbsp;|&nbsp; {article.language}
                      </span>
                      <div className="flex items-center space-x-1">
                        {expandable.has(article.id) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleArticle(article.id)}
                            className="text-green-600 hover:text-green-400 p-0.5"
                          >
                            {isExpanded ? (
                              <>
                                Show Less{" "}
                                <ChevronUp className="h-3 w-3 ml-0.5 text-green-600" />
                              </>
                            ) : (
                              <>
                                Read More{" "}
                                <ChevronDown className="h-3 w-3 ml-0.5 text-green-600" />
                              </>
                            )}
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-green-600 hover:text-green-400 p-0.5"
                        >
                          Share{" "}
                          <ExternalLink className="h-3 w-3 ml-0.5 text-green-600" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
            {/* If no results found during search */}
            {searchResults !== null && searchResults.length === 0 && (
              <p className="col-span-full text-center text-[#7E7E85]">
                No matching articles found.
              </p>
            )}
          </div>
        )}

        {/* About Section (hide during search) */}
        {searchResults === null && (
          <section className="mt-10">
            <Card className="bg-[#162F61] border border-[#0A1C3B] text-white p-6 rounded-md">
              <div className="text-center max-w-3xl mx-auto">
                <h2 className="text-xl font-semibold mb-3 text-white">
                  About EarthMC Live
                </h2>
                <p className="text-sm text-white mb-4">
                  EarthMC Live is the streamlined source for up-to-date news,
                  events, and community updates from the EarthMC Minecraft
                  server. We focus on clarity and minimalism—no distractions,
                  just the essentials.
                </p>
                <div className="flex flex-wrap justify-center gap-3">
                  {["Real-time Updates", "Community Focus", "Server News"].map(
                    (badge) => (
                      <Badge
                        key={badge}
                        variant="secondary"
                        className="bg-green-800 text-white text-xs py-0.5 px-2 rounded"
                      >
                        {badge}
                      </Badge>
                    )
                  )}
                </div>
              </div>
            </Card>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-[#0F254D] border-t border-[#0A1C3B] py-4">
        <div className="container mx-auto px-4 text-center text-xs text-[#7E7E85]">
          <p className="text-white">
            EarthMC Live — Unofficial Community News Portal
          </p>
          <p className="mt-1 text-green-600">
            Built with React & Tailwind CSS • Not affiliated with Mojang Studios
          </p>
          <p className="mt-2 text-white">Credit to charilaos & heroharley</p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
