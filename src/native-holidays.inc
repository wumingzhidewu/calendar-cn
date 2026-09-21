// Native calendar holiday badges. GPL-3.0-or-later.
// CalendarViewDayItem renders its dates itself, above its custom template.
#include <fstream>
#include <winrt/Windows.UI.Composition.h>
#include <winrt/Windows.UI.Xaml.Hosting.h>
#include <winrt/Windows.Globalization.h>
#include <winrt/Windows.UI.Xaml.Automation.h>

namespace NativeHolidays {
using namespace winrt::Windows::UI::Xaml;
using namespace winrt::Windows::UI::Xaml::Controls;
struct Entry { bool off; std::wstring name; };
struct ItemState {
    winrt::weak_ref<CalendarViewDayItem> item;
    Canvas overlay{nullptr}, moving{nullptr};
    winrt::weak_ref<ScrollViewer> scroller;
    winrt::Windows::UI::Composition::CompositionPropertySet scrollProperties{nullptr};
    winrt::Windows::UI::Composition::Visual movingVisual{nullptr};
    winrt::Windows::Foundation::Rect lastBounds{-1,-1,-1,-1}, lastClip{-1,-1,-1,-1};
    Border tint{nullptr}, badge{nullptr};
    TextBlock label{nullptr};
    winrt::Windows::Foundation::IInspectable originalTip{nullptr};
    bool modified = false;
    int lastDate = 0, lastKind = 0;
    std::wstring lastName;
    double width = -1, height = -1;
};
thread_local std::unordered_map<uintptr_t, ItemState> items;
thread_local bool renderingAttached = false;
thread_local bool ticking = false;
thread_local winrt::event_token tickToken{};
thread_local std::map<int, Entry> holidays;
thread_local ULONGLONG lastRead = 0;
thread_local bool stopping = false;
thread_local std::vector<winrt::weak_ref<CalendarView>> calendarViews;
thread_local int reportedHeight = -1;

std::filesystem::path DataPath() {
    wchar_t path[32768];
    auto len = GetModuleFileNameW(GetCurrentModuleHandle(), path, ARRAYSIZE(path));
    return std::filesystem::path(std::wstring(path, len)).parent_path() / L"holidays.tsv";
}

void ReadData() {
    auto now = GetTickCount64();
    if (lastRead && now - lastRead < 60000) return;
    lastRead = now;
    std::ifstream stream(DataPath());
    if (!stream) return;
    std::map<int, Entry> next;
    std::string line;
    while (std::getline(stream, line)) {
        if (line.empty() || line[0] == '#') continue;
        if (line.size() < 12 || line[8] != '\t' || line[10] != '\t') continue;
        int date = 0;
        auto [ptr, ec] = std::from_chars(line.data(), line.data()+8, date);
        if (ec != std::errc{} || ptr != line.data()+8 || date < 20000101 || date > 21001231) continue;
        if (line[9] != '0' && line[9] != '1') continue;
        if (!line.empty() && line.back() == '\r') line.pop_back();
        next[date] = {line[9] == '1', std::wstring(winrt::to_hstring(line.substr(11)))};
    }
    if (!next.empty()) {
        holidays.swap(next);
        Wh_SetIntValue(L"HolidayDataCount", static_cast<int>(holidays.size()));
    }
}

// Overlay belongs to CalendarCenterGrid, never to a day item or CalendarPanel.
// Native templates, fonts, measurement and date virtualization remain untouched.
void Restore(CalendarViewDayItem const& item, ItemState& state) {
    if (state.movingVisual) state.movingVisual.Properties().StopAnimation(L"Translation");
    if (state.overlay) {
        auto parent = Media::VisualTreeHelper::GetParent(state.overlay);
        if (auto panel = parent.try_as<Panel>()) {
            uint32_t index;
            if (panel.Children().IndexOf(state.overlay, index)) panel.Children().RemoveAt(index);
        } else if (auto border = parent.try_as<Border>()) {
            if (border.Child() == state.overlay) border.Child(nullptr);
        }
    }
    if (state.modified && item) {
        if (state.originalTip == DependencyProperty::UnsetValue())
            item.ClearValue(ToolTipService::ToolTipProperty());
        else item.SetValue(ToolTipService::ToolTipProperty(), state.originalTip);
    }
    state.movingVisual = nullptr; state.scrollProperties = nullptr; state.moving = nullptr;
    state.overlay = nullptr; state.tint = nullptr; state.badge = nullptr; state.label = nullptr;
    state.modified = false; state.width = -1; state.height = -1;
}

bool Attach(CalendarViewDayItem const& item, ItemState& state) {
    if (item.ActualWidth() < 18 || item.ActualHeight() < 18) return false;
    Grid root{nullptr};
    ScrollViewer scroller{nullptr};
    DependencyObject parent = item;
    for (int depth = 0; parent && depth < 32; ++depth) {
        if (!scroller) scroller = parent.try_as<ScrollViewer>();
        auto grid = parent.try_as<Grid>();
        if (grid && grid.Name() == L"CalendarCenterGrid") { root = grid; break; }
        parent = Media::VisualTreeHelper::GetParent(parent);
    }
    if (!root || !scroller || !scroller.Content().try_as<UIElement>()) return false;
    state.originalTip = item.ReadLocalValue(ToolTipService::ToolTipProperty());
    Canvas overlay;
    Grid::SetRowSpan(overlay, 32); Grid::SetColumnSpan(overlay, 32);
    overlay.Name(L"CalendarCnHolidayOverlay");
    overlay.IsHitTestVisible(false);
    Border tint;
    tint.CornerRadius(CornerRadius{4});
    Border badge;
    badge.Width(14); badge.Height(14); badge.CornerRadius(CornerRadius{3});
    TextBlock label;
    label.FontFamily(Media::FontFamily(L"Microsoft YaHei UI"));
    label.FontSize(10);
    label.FontWeight(winrt::Windows::UI::Text::FontWeights::SemiBold());
    label.Foreground(Media::SolidColorBrush(winrt::Windows::UI::Color{255,255,255,255}));
    label.HorizontalAlignment(HorizontalAlignment::Center);
    label.VerticalAlignment(VerticalAlignment::Center);
    badge.Child(label);
    Canvas moving;
    moving.IsHitTestVisible(false);
    moving.Children().Append(tint); moving.Children().Append(badge);
    overlay.Children().Append(moving);
    using Hosting::ElementCompositionPreview;
    ElementCompositionPreview::SetIsTranslationEnabled(moving, true);
    auto visual = ElementCompositionPreview::GetElementVisual(moving);
    auto properties = ElementCompositionPreview::GetScrollViewerManipulationPropertySet(scroller);
    auto animation = visual.Compositor().CreateExpressionAnimation(L"scroll.Translation");
    animation.SetReferenceParameter(L"scroll", properties);
    visual.Properties().StartAnimation(L"Translation", animation);
    root.Children().Append(overlay);
    state.moving = moving; state.movingVisual = visual;
    state.scrollProperties = properties; state.scroller = winrt::make_weak(scroller);
    state.lastBounds = {-1,-1,-1,-1}; state.lastClip = {-1,-1,-1,-1};
    state.overlay = overlay; state.tint = tint; state.badge = badge; state.label = label;
    state.modified = true;
    state.lastKind = -1;
    return true;
}

void Paint(CalendarViewDayItem const& item, ItemState& state, bool off, std::wstring const& name) {
    auto color = off ? winrt::Windows::UI::Color{255,22,131,75} : winrt::Windows::UI::Color{255,184,91,0};
    state.badge.Background(Media::SolidColorBrush(color));
    color.A = 24;
    state.tint.Background(Media::SolidColorBrush(color));
    state.label.Text(off ? L"休" : L"班");
    ToolTipService::SetToolTip(item, winrt::box_value(name + (off ? L" · 放假（休）" : L" · 调休上班（班）")));
}

void Position(CalendarViewDayItem const& item, ItemState& state) {
    using winrt::Windows::Foundation::Rect;
    double width = item.ActualWidth(), height = item.ActualHeight();
    auto scroller = state.scroller.get();
    if (!scroller) { state.overlay.Visibility(Visibility::Collapsed); return; }
    auto content = scroller.Content().try_as<UIElement>();
    if (!content) { state.overlay.Visibility(Visibility::Collapsed); return; }
    // Date positions stay in content coordinates. The compositor supplies scroll
    // translation continuously, including inertia while the UI thread is busy.
    auto bounds = item.TransformToVisual(content).TransformBounds(Rect{0,0,(float)width,(float)height});
    auto viewport = scroller.TransformToVisual(state.overlay).TransformBounds(
        Rect{0,0,(float)scroller.ActualWidth(),(float)scroller.ActualHeight()});
    float left=viewport.X, top=viewport.Y, right=left+viewport.Width, bottom=top+viewport.Height;
    DependencyObject parent = scroller;
    bool visible=true;
    for (int depth=0; parent && depth<32; ++depth) {
        if (auto e=parent.try_as<FrameworkElement>()) {
            if (e.Visibility()!=Visibility::Visible) visible=false;
            if (e.try_as<ScrollViewer>() || e.Name()==L"CalendarCenterGrid") {
                auto clip=e.TransformToVisual(state.overlay).TransformBounds(Rect{0,0,(float)e.ActualWidth(),(float)e.ActualHeight()});
                left=std::max(left,clip.X); top=std::max(top,clip.Y);
                right=std::min(right,clip.X+clip.Width); bottom=std::min(bottom,clip.Y+clip.Height);
            }
            if (e.Name()==L"CalendarCenterGrid") break;
        }
        parent=Media::VisualTreeHelper::GetParent(parent);
    }
    // Do not hide offscreen dates based on a sampled scroll offset: their clip
    // and compositor animation must allow them to enter the viewport mid-scroll.
    visible=visible && right>left && bottom>top && width>=18 && height>=18;
    auto visibility=visible ? Visibility::Visible : Visibility::Collapsed;
    if(state.overlay.Visibility()!=visibility) state.overlay.Visibility(visibility);
    if (!visible) return;
    Rect clipping{left,top,right-left,bottom-top};
    if (clipping != state.lastClip) {
        Media::RectangleGeometry clip; clip.Rect(clipping); state.overlay.Clip(clip);
        state.lastClip=clipping;
    }
    bounds.X += viewport.X; bounds.Y += viewport.Y;
    if(bounds != state.lastBounds) {
        Canvas::SetLeft(state.tint,bounds.X+1); Canvas::SetTop(state.tint,bounds.Y+1);
        state.tint.Width(std::max(0.0,width-2)); state.tint.Height(std::max(0.0,height-2));
        Canvas::SetLeft(state.badge,bounds.X+std::max(0.0,width-15)); Canvas::SetTop(state.badge,bounds.Y+1);
        state.lastBounds=bounds;
    }
    state.width=width; state.height=height;
}

void Tick() noexcept {
    if (stopping || ticking) return;
    ticking = true;
    struct TickGuard { ~TickGuard() { ticking = false; } } reset;
    try {
        ReadData();
        int calendarHeight = 0;
        auto views = calendarViews;
        for (auto const& weak : views) if (auto view = weak.get())
            calendarHeight = std::max(calendarHeight, static_cast<int>(view.ActualHeight()));
        if (calendarHeight != reportedHeight) {
            Wh_SetIntValue(L"CalendarViewHeight", calendarHeight);
            reportedHeight = calendarHeight;
        }
        // Snapshot because adding/removing visual decorations can reenter diagnostics.
        std::vector<uintptr_t> keys;
        for (auto const& [key, state] : items) keys.push_back(key);
        winrt::Windows::Globalization::Calendar calendar;
        calendar.ChangeCalendarSystem(L"GregorianCalendar");
        for (auto key : keys) {
            auto it = items.find(key);
            if (it == items.end()) continue;
            auto item = it->second.item.get();
            if (!item) {
                auto dead=it->second;
                Restore(nullptr, dead);
                items.erase(key); continue;
            }
            auto state = it->second;
            calendar.SetDateTime(item.Date());
            int date = calendar.Year()*10000 + calendar.Month()*100 + calendar.Day();
            auto found = holidays.find(date);
            int kind = found == holidays.end() ? 0 : (found->second.off ? 1 : 2);
            std::wstring name = kind ? found->second.name : L"";
            if (state.modified && (state.lastDate != date || !state.overlay ||
                !Media::VisualTreeHelper::GetParent(state.overlay))) Restore(item, state);
            if (!kind) {
                Restore(item, state);
            } else {
                if (!state.modified && !Attach(item, state)) { items[key] = state; continue; }
                if (state.lastDate != date || state.lastKind != kind || state.lastName != name) {
                    Paint(item, state, kind == 1, name);
                    wchar_t status[128];
                    swprintf_s(status, L"%d %s %s", date, kind == 1 ? L"休" : L"班", name.c_str());
                    Wh_SetStringValue(L"HolidayLastRendered", status);
                }
                Position(item, state);
            }
            state.lastDate = date;
            state.lastKind = kind;
            state.lastName = std::move(name);
            items[key] = state;
        }
    } catch (winrt::hresult_error const& e) {
        Wh_SetStringValue(L"HolidayLastError", e.message().c_str());
        Wh_Log(L"Holiday badges: %08X %s", e.code(), e.message().c_str());
    } catch (...) { Wh_Log(L"Holiday badges: unexpected error"); }
}

void Track(FrameworkElement const& element) noexcept {
    if (stopping) return;
    try {
        if (auto view = element.try_as<CalendarView>()) {
            bool found = false;
            for (auto const& weak : calendarViews) if (weak.get() == view) { found = true; break; }
            if (!found) calendarViews.push_back(winrt::make_weak(view));
        }
        auto item = element.try_as<CalendarViewDayItem>();
        if (!item) return;
        if (items.size() >= 1024) return; // Bound work if the host has a layout fault.
        auto key = reinterpret_cast<uintptr_t>(winrt::get_abi(item));
        auto it = items.find(key);
        if (it == items.end() || !it->second.item.get()) {
            ItemState state;
            state.item = winrt::make_weak(item);
            items.insert_or_assign(key, std::move(state));
            Wh_SetIntValue(L"HolidayTrackedItems", static_cast<int>(items.size()));
        }
        if (!renderingAttached) {
            Wh_SetStringValue(L"HolidayRenderer", L"compositor-scroll-overlay-v2");
            tickToken = Media::CompositionTarget::Rendering([](auto const&, auto const&) { Tick(); });
            renderingAttached = true;
        }
    } catch (...) { Wh_Log(L"Holiday badge tracking failed"); }
}

void Stop() noexcept {
    stopping = true;
    try {
        if (renderingAttached) { Media::CompositionTarget::Rendering(tickToken); renderingAttached = false; }
        auto old = std::move(items);
        items.clear();
        calendarViews.clear();
        reportedHeight = -1;
        for (auto& [key,state] : old) {
            try { Restore(state.item.get(), state); } catch (...) {}
        }
        holidays.clear();
        lastRead = 0;
    } catch (...) {}
    stopping = false;
}
}
