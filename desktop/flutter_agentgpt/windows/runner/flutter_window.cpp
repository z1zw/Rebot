#include "flutter_window.h"

#include <optional>

#include "flutter/generated_plugin_registrant.h"
#include "flutter/method_channel.h"
#include "flutter/standard_method_codec.h"
#include <tlhelp32.h>

namespace {
constexpr char kEmbedChannelName[] = "rebot.emulator.embed";

struct FindWindowData {
  std::wstring needle;
  HWND found = nullptr;
};

BOOL CALLBACK EnumWindowsProc(HWND hwnd, LPARAM lparam) {
  auto* data = reinterpret_cast<FindWindowData*>(lparam);
  wchar_t title[512] = {0};
  GetWindowTextW(hwnd, title, 512);
  std::wstring wtitle(title);
  if (!wtitle.empty() && wtitle.find(data->needle) != std::wstring::npos) {
    data->found = hwnd;
    return FALSE;
  }
  return TRUE;
}

HWND FindWindowByTitleContains(const std::wstring& title) {
  FindWindowData data{title, nullptr};
  EnumWindows(EnumWindowsProc, reinterpret_cast<LPARAM>(&data));
  return data.found;
}

DWORD FindProcessIdByName(const std::wstring& name) {
  HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
  if (snapshot == INVALID_HANDLE_VALUE) return 0;
  PROCESSENTRY32W entry = {};
  entry.dwSize = sizeof(entry);
  if (Process32FirstW(snapshot, &entry)) {
    do {
      if (name == entry.szExeFile) {
        CloseHandle(snapshot);
        return entry.th32ProcessID;
      }
    } while (Process32NextW(snapshot, &entry));
  }
  CloseHandle(snapshot);
  return 0;
}

struct FindPidWindowData {
  DWORD pid;
  HWND found = nullptr;
};

BOOL CALLBACK EnumWindowsByPidProc(HWND hwnd, LPARAM lparam) {
  auto* data = reinterpret_cast<FindPidWindowData*>(lparam);
  DWORD pid = 0;
  GetWindowThreadProcessId(hwnd, &pid);
  if (pid == data->pid && IsWindowVisible(hwnd)) {
    data->found = hwnd;
    return FALSE;
  }
  return TRUE;
}

HWND FindWindowByProcessName(const std::wstring& exe_name) {
  DWORD pid = FindProcessIdByName(exe_name);
  if (!pid) return nullptr;
  FindPidWindowData data{pid, nullptr};
  EnumWindows(EnumWindowsByPidProc, reinterpret_cast<LPARAM>(&data));
  return data.found;
}

void SetChildWindow(HWND parent, HWND child, int x, int y, int width,
                    int height) {
  if (!child || !parent) return;
  POINT pt = {x, y};
  ScreenToClient(parent, &pt);
  LONG_PTR style = GetWindowLongPtr(child, GWL_STYLE);
  style &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_MINIMIZE | WS_MAXIMIZE |
             WS_SYSMENU);
  style |= WS_CHILD | WS_VISIBLE;
  SetWindowLongPtr(child, GWL_STYLE, style);
  LONG_PTR ex_style = GetWindowLongPtr(child, GWL_EXSTYLE);
  ex_style &= ~(WS_EX_APPWINDOW);
  SetWindowLongPtr(child, GWL_EXSTYLE, ex_style);
  SetParent(child, parent);
  SetWindowPos(child, HWND_TOP, pt.x, pt.y, width, height,
               SWP_NOACTIVATE | SWP_FRAMECHANGED);
  ShowWindow(child, SW_SHOW);
}
}  // namespace

FlutterWindow::FlutterWindow(const flutter::DartProject& project)
    : project_(project) {}

FlutterWindow::~FlutterWindow() {}

bool FlutterWindow::OnCreate() {
  if (!Win32Window::OnCreate()) {
    return false;
  }

  RECT frame = GetClientArea();

  // The size here must match the window dimensions to avoid unnecessary surface
  // creation / destruction in the startup path.
  flutter_controller_ = std::make_unique<flutter::FlutterViewController>(
      frame.right - frame.left, frame.bottom - frame.top, project_);
  // Ensure that basic setup of the controller was successful.
  if (!flutter_controller_->engine() || !flutter_controller_->view()) {
    return false;
  }
  RegisterPlugins(flutter_controller_->engine());
  SetChildContent(flutter_controller_->view()->GetNativeWindow());

  auto channel = std::make_unique<flutter::MethodChannel<flutter::EncodableValue>>(
      flutter_controller_->engine()->messenger(), kEmbedChannelName,
      &flutter::StandardMethodCodec::GetInstance());
  channel->SetMethodCallHandler(
      [this](const flutter::MethodCall<flutter::EncodableValue>& call,
             std::unique_ptr<flutter::MethodResult<flutter::EncodableValue>>
                 result) {
        if (call.method_name() == "embedWindow") {
          const auto* args = std::get_if<flutter::EncodableMap>(call.arguments());
          if (!args) {
            result->Error("bad_args", "Expected map arguments.");
            return;
          }
          std::wstring title;
          std::wstring process;
          auto get_int = [](const flutter::EncodableMap& map,
                            const std::string& key) -> int {
            auto it = map.find(flutter::EncodableValue(key));
            if (it == map.end()) return 0;
            if (auto val = std::get_if<int>( &it->second)) return *val;
            if (auto val64 = std::get_if<int64_t>(&it->second)) return static_cast<int>(*val64);
            return 0;
          };
          int x = 0, y = 0, width = 0, height = 0;
          auto it_title = args->find(flutter::EncodableValue("title"));
          if (it_title != args->end()) {
            auto title_str = std::get<std::string>(it_title->second);
            title = std::wstring(title_str.begin(), title_str.end());
          }
          auto it_proc = args->find(flutter::EncodableValue("process"));
          if (it_proc != args->end()) {
            auto proc_str = std::get<std::string>(it_proc->second);
            process = std::wstring(proc_str.begin(), proc_str.end());
          }
          x = get_int(*args, "x");
          y = get_int(*args, "y");
          width = get_int(*args, "width");
          height = get_int(*args, "height");

          HWND hwnd = nullptr;
          if (!process.empty()) {
            hwnd = FindWindowByProcessName(process);
          }
          if (!hwnd && !title.empty()) {
            hwnd = FindWindowByTitleContains(title);
          }
          if (!hwnd) {
            result->Error("not_found", "Window not found.");
            return;
          }
          embedded_window_ = hwnd;
          HWND parent = flutter_controller_->view()->GetNativeWindow();
          SetChildWindow(parent, hwnd, x, y, width, height);
          result->Success(flutter::EncodableValue(true));
          return;
        }
        if (call.method_name() == "resizeWindow") {
          const auto* args = std::get_if<flutter::EncodableMap>(call.arguments());
          if (!args || !embedded_window_) {
            result->Success(flutter::EncodableValue(false));
            return;
          }
          auto get_int = [](const flutter::EncodableMap& map,
                            const std::string& key) -> int {
            auto it = map.find(flutter::EncodableValue(key));
            if (it == map.end()) return 0;
            if (auto val = std::get_if<int>(&it->second)) return *val;
            if (auto val64 = std::get_if<int64_t>(&it->second)) return static_cast<int>(*val64);
            return 0;
          };
          int x = get_int(*args, "x");
          int y = get_int(*args, "y");
          int width = get_int(*args, "width");
          int height = get_int(*args, "height");
          POINT pt = {x, y};
          HWND parent = flutter_controller_->view()->GetNativeWindow();
          ScreenToClient(parent, &pt);
          SetWindowPos(embedded_window_, HWND_TOP, pt.x, pt.y, width, height,
                       SWP_NOACTIVATE | SWP_FRAMECHANGED);
          result->Success(flutter::EncodableValue(true));
          return;
        }
        if (call.method_name() == "unembedWindow") {
          if (embedded_window_) {
            SetParent(embedded_window_, nullptr);
            ShowWindow(embedded_window_, SW_SHOW);
            embedded_window_ = nullptr;
          }
          result->Success(flutter::EncodableValue(true));
          return;
        }
        result->NotImplemented();
      });

  flutter_controller_->engine()->SetNextFrameCallback([&]() {
    this->Show();
  });

  // Flutter can complete the first frame before the "show window" callback is
  // registered. The following call ensures a frame is pending to ensure the
  // window is shown. It is a no-op if the first frame hasn't completed yet.
  flutter_controller_->ForceRedraw();

  return true;
}

void FlutterWindow::OnDestroy() {
  if (flutter_controller_) {
    flutter_controller_ = nullptr;
  }

  Win32Window::OnDestroy();
}

LRESULT
FlutterWindow::MessageHandler(HWND hwnd, UINT const message,
                              WPARAM const wparam,
                              LPARAM const lparam) noexcept {
  // Give Flutter, including plugins, an opportunity to handle window messages.
  if (flutter_controller_) {
    std::optional<LRESULT> result =
        flutter_controller_->HandleTopLevelWindowProc(hwnd, message, wparam,
                                                      lparam);
    if (result) {
      return *result;
    }
  }

  switch (message) {
    case WM_FONTCHANGE:
      flutter_controller_->engine()->ReloadSystemFonts();
      break;
  }

  return Win32Window::MessageHandler(hwnd, message, wparam, lparam);
}
