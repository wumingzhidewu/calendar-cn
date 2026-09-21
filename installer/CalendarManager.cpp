#include <windows.h>
#include <shellapi.h>
#include <string>
#include <vector>
#include <iterator>
#include "theme_names.inc"

std::wstring root;
HFONT font;
HWND note;
HWND themeCombo, backgroundCombo;
#ifdef THEME_PICKER_ONLY
constexpr int noteY=168;
#else
constexpr int noteY=300;
#endif

std::wstring ReadText(const std::wstring& file) {
    HANDLE handle = CreateFileW(file.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING, 0, nullptr);
    if (handle == INVALID_HANDLE_VALUE) return L"";
    DWORD length = GetFileSize(handle, nullptr);
    if (length > 65536) { CloseHandle(handle); return L""; }
    std::string bytes(length, 0); DWORD got = 0;
    ReadFile(handle, bytes.data(), length, &got, nullptr); CloseHandle(handle);
    size_t start = got >= 3 && bytes.substr(0,3) == "\xef\xbb\xbf" ? 3 : 0;
    int count = MultiByteToWideChar(CP_UTF8, 0, bytes.data()+start, got-static_cast<DWORD>(start), nullptr, 0);
    std::wstring text(count, 0);
    MultiByteToWideChar(CP_UTF8, 0, bytes.data()+start, got-static_cast<DWORD>(start), text.data(), count);
    return text;
}

std::wstring SelectedValue(const std::wstring& json,const wchar_t* key) {
    auto at=json.find(L"\""+std::wstring(key)+L"\"");
    if(at==std::wstring::npos) return L"";
    at=json.find(L':',at); if(at==std::wstring::npos) return L"";
    auto begin=json.find(L'"',at);if(begin==std::wstring::npos) return L"";
    auto end=json.find(L'"',begin+1);if(end==std::wstring::npos) return L"";
    return json.substr(begin+1,end-begin-1);
}

int Run(const wchar_t* action, const wchar_t* themeId=nullptr, const wchar_t* backgroundMode=L"art") {
    wchar_t system[MAX_PATH]; GetSystemDirectoryW(system, MAX_PATH);
    std::wstring exe = std::wstring(system) + L"\\WindowsPowerShell\\v1.0\\powershell.exe";
    std::wstring script = themeId ? L"Theme.ps1" : L"Runtime.ps1";
    std::wstring command = L"\"" + exe + L"\" -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File \"" + root + L"\\" + script + L"\" -Action " + action + L" -RuntimePath \"" + root + L"\"";
    if(themeId) command += L" -ThemeId " + std::wstring(themeId) + L" -BackgroundMode " + backgroundMode;
    STARTUPINFOW si{sizeof(si)}; si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi{};
    if (!CreateProcessW(exe.c_str(), command.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr, root.c_str(), &si, &pi)) return 2;
    CloseHandle(pi.hThread);
    DWORD waited = WaitForSingleObject(pi.hProcess, 45000), code = 1;
    if (waited == WAIT_OBJECT_0) GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hProcess);
    return static_cast<int>(code);
}

void Add(HWND parent, const wchar_t* type, const wchar_t* text, int id, int x, int y, int width, int height) {
    HWND child = CreateWindowW(type, text, WS_CHILD | WS_VISIBLE | (id ? WS_TABSTOP : 0), x, y, width, height, parent, reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)), nullptr, nullptr);
    SendMessageW(child, WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE);
    if (id == 0 && y == noteY) note = child;
}

LRESULT CALLBACK WindowProc(HWND hwnd, UINT message, WPARAM wp, LPARAM lp) {
    switch (message) {
    case WM_CREATE:
#ifdef THEME_PICKER_ONLY
        Add(hwnd,L"STATIC",L"选择主题和背景，应用到 Windows 原生日历。",0,22,18,425,25);
        Add(hwnd,L"STATIC",L"日历主题",0,22,48,250,25);
        {
        constexpr int comboY=76,applyY=72,backgroundY=120,labelY=124;
#else
        Add(hwnd,L"STATIC",L"保留原生日历，放假和补班一眼看清。",0,22,18,420,25);
        Add(hwnd,L"STATIC",L"绿色“休”：放假    橙色“班”：调休上班",0,22,49,420,25);
        Add(hwnd,L"BUTTON",L"启用标记",101,22,90,130,34);
        Add(hwnd,L"BUTTON",L"暂停本次",102,167,90,130,34);
        Add(hwnd,L"BUTTON",L"立即更新数据",103,312,90,130,34);
        Add(hwnd,L"BUTTON",L"查看状态",104,22,138,130,34);
        Add(hwnd,L"BUTTON",L"使用说明",105,167,138,130,34);
        Add(hwnd,L"BUTTON",L"卸载",106,312,138,130,34);
        Add(hwnd,L"STATIC",L"日历主题",0,22,184,250,25);
        {
        constexpr int comboY=214,applyY=210,backgroundY=254,labelY=258;
#endif
        themeCombo=CreateWindowW(L"COMBOBOX",L"",WS_CHILD|WS_VISIBLE|WS_TABSTOP|CBS_DROPDOWNLIST|WS_VSCROLL,22,comboY,275,310,hwnd,(HMENU)107,nullptr,nullptr);
        SendMessageW(themeCombo,WM_SETFONT,(WPARAM)font,TRUE);
        for(const auto& theme:kThemes) SendMessageW(themeCombo,CB_ADDSTRING,0,(LPARAM)theme.label);
        SendMessageW(themeCombo,CB_SETCURSEL,0,0);
        Add(hwnd,L"BUTTON",L"应用主题",108,312,applyY,130,34);
        Add(hwnd,L"STATIC",L"背景",0,22,labelY,72,25);
        backgroundCombo=CreateWindowW(L"COMBOBOX",L"",WS_CHILD|WS_VISIBLE|WS_TABSTOP|CBS_DROPDOWNLIST,110,backgroundY,187,150,hwnd,(HMENU)109,nullptr,nullptr);
        SendMessageW(backgroundCombo,WM_SETFONT,(WPARAM)font,TRUE);
        for(auto label:{L"插画背景",L"渐变底色",L"纯色背景"}) SendMessageW(backgroundCombo,CB_ADDSTRING,0,(LPARAM)label);
        SendMessageW(backgroundCombo,CB_SETCURSEL,0,0);
        {
            auto saved=ReadText(root+L"\\selected-theme.json");
            auto id=SelectedValue(saved,L"id"),mode=SelectedValue(saved,L"backgroundMode");
            for(size_t i=0;i<std::size(kThemes);i++) if(id==kThemes[i].id) SendMessageW(themeCombo,CB_SETCURSEL,i,0);
            if(mode==L"gradient") SendMessageW(backgroundCombo,CB_SETCURSEL,1,0);
            else if(mode==L"solid") SendMessageW(backgroundCombo,CB_SETCURSEL,2,0);
        }
        Add(hwnd,L"STATIC",L"主题保留休／班标记。选择“系统默认”可恢复外观。",0,22,noteY,425,48);
        }
        return 0;
    case WM_COMMAND: {
        int id = LOWORD(wp);
        if(id==107 || id==109) return 0;
        if(id==108) {
            auto index=SendMessageW(themeCombo,CB_GETCURSEL,0,0);
            auto background=SendMessageW(backgroundCombo,CB_GETCURSEL,0,0);
            if(index<0 || (size_t)index>=std::size(kThemes)) return 0;
            const wchar_t* modes[]={L"art",L"gradient",L"solid"};
            if(background<0 || background>2) background=0;
            SetWindowTextW(note,L"正在应用主题……");UpdateWindow(hwnd);
            if(Run(L"Apply",kThemes[index].id,modes[background])==0) {
                const wchar_t* labels[]={L"插画背景",L"渐变底色",L"纯色背景"};
                auto message=std::wstring(L"已应用：")+kThemes[index].label+L" · "+labels[background]+L"。重新展开日历查看。";
                SetWindowTextW(note,message.c_str());
            }
            else {auto error=ReadText(root+L"\\last-error.txt");MessageBoxW(hwnd,error.c_str(),L"主题未应用",MB_OK|MB_ICONINFORMATION);SetWindowTextW(note,L"原有日历标记保持可用。");}
            return 0;
        }
        if (id == 105) {
            ShellExecuteW(hwnd,L"open",(root+L"\\使用说明.html").c_str(),nullptr,nullptr,SW_SHOWNORMAL); return 0;
        }
        if (id == 106) {
            if (MessageBoxW(hwnd,L"卸载后将恢复 Windows 原生日历，并移除自动启动和数据更新任务。是否继续？",L"卸载中国节假日日历",MB_YESNO|MB_ICONQUESTION) == IDYES) {
                auto result = ShellExecuteW(hwnd,L"open",(root+L"\\Uninstall.exe").c_str(),nullptr,root.c_str(),SW_SHOWNORMAL);
                if (reinterpret_cast<INT_PTR>(result) > 32) DestroyWindow(hwnd);
            }
            return 0;
        }
        const wchar_t* action = id==101 ? L"Enable" : id==102 ? L"Stop" : id==103 ? L"Update" : L"Status";
        SetWindowTextW(note,L"正在处理……"); UpdateWindow(hwnd);
        int result = Run(action);
        if (result != 0) {
            std::wstring error = ReadText(root+L"\\last-error.txt");
            MessageBoxW(hwnd,error.empty()?L"操作未完成，请稍后重试。":error.c_str(),L"中国节假日日历",MB_OK|MB_ICONINFORMATION);
            SetWindowTextW(note,L"操作未完成。");
        } else if (id == 104) {
            std::wstring text = ReadText(root+L"\\status-report.txt");
            MessageBoxW(hwnd,text.c_str(),L"运行状态",MB_OK|MB_ICONINFORMATION);
            SetWindowTextW(note,L"登录后自动启用，节假日数据自动更新。");
        } else {
            SetWindowTextW(note,id==101?L"已请求启用，请点击右下角时间查看。":id==102?L"已暂停。本次会话保持关闭，下次登录自动启用。":L"已开始后台检查，稍后可点击“查看状态”。");
        }
        return 0;
    }
    case WM_DESTROY: PostQuitMessage(0); return 0;
    }
    return DefWindowProcW(hwnd,message,wp,lp);
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR command, int show) {
    wchar_t module[32768]; GetModuleFileNameW(nullptr,module,32768);
    root=module; root.resize(root.find_last_of(L"\\/"));
    if (wcscmp(command,L"--startup")==0) return Run(L"Start");
    if (wcscmp(command,L"--enable")==0) return Run(L"Enable");
    if (wcscmp(command,L"--stop")==0) return Run(L"Stop");
    if (wcscmp(command,L"--status")==0) return Run(L"Status");
    SetProcessDPIAware();
    font=CreateFontW(-17,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,CLEARTYPE_QUALITY,DEFAULT_PITCH,L"Microsoft YaHei UI");
    WNDCLASSW wc{}; wc.lpfnWndProc=WindowProc; wc.hInstance=instance; wc.lpszClassName=L"NativeCalendarHolidayManager"; wc.hCursor=LoadCursor(nullptr,IDC_ARROW); wc.hbrBackground=(HBRUSH)(COLOR_WINDOW+1); wc.hIcon=LoadIcon(nullptr,IDI_APPLICATION);
    RegisterClassW(&wc);
#ifdef THEME_PICKER_ONLY
    const wchar_t* title=L"日历主题 · calendar-cn";constexpr int height=267;
#else
    const wchar_t* title=L"中国节假日日历 · 预览版";constexpr int height=397;
#endif
    HWND hwnd=CreateWindowExW(0,wc.lpszClassName,title,WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX,CW_USEDEFAULT,CW_USEDEFAULT,485,height,nullptr,nullptr,instance,nullptr);
    ShowWindow(hwnd,show); UpdateWindow(hwnd);
    MSG msg{};
    while(GetMessageW(&msg,nullptr,0,0)>0) { if(!IsDialogMessageW(hwnd,&msg)){TranslateMessage(&msg);DispatchMessageW(&msg);} }
    DeleteObject(font); return 0;
}
