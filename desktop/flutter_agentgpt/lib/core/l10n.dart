class S {
  S._();

  static String get appName => "Rebot";
  static String get appTitle => "Rebot Workspace";

  static String get explorer => "EXPLORER";
  static String get skills => "SKILL REGISTRY";
  static String get settings => "SETTINGS";
  static String get history => "HISTORY";
  static String get agents => "AGENTS";
  static String get console => "Console";
  static String get terminal => "Terminal";
  static String get network => "Network";
  static String get preview => "Preview";
  static String get devServer => "DEV SERVER";

  static String get search => "Search";
  static String get searchFiles => "Search files...";
  static String get cancel => "Cancel";
  static String get create => "Create";
  static String get save => "Save";
  static String get close => "Close";
  static String get delete => "Delete";
  static String get refresh => "Refresh";
  static String get retry => "Try Again";
  static String get copyPath => "Copy Path";
  static String get copied => "Copied!";
  static String get confirm => "Confirm";

  static String get createFile => "Create File";
  static String get createFolder => "Create Folder";
  static String get newFile => "New file";
  static String get newFolder => "New folder";

  static String get noFilesYet => "No files yet";
  static String get filesAppearHere => "Files will appear here as\nthe agent generates code";
  static String get noExecutions => "No executions yet";
  static String get noAgents => "No agents found";

  static String get running => "Running";
  static String get idle => "Idle";
  static String get connecting => "Connecting...";
  static String get active => "Active";
  static String get inactive => "Inactive";
  static String get stopped => "Stopped";
  static String get online => "Online";
  static String get offline => "Offline";

  static String get somethingWentWrong => "Something went wrong";
  static String get networkError => "Network connection failed";
  static String get timeout => "Request timed out";

  static String get newProject => "New Project";
  static String get projectName => "Project Name";
  static String get projectDescription => "Description";
  static String get projectType => "Project Type";
  static String get workspace => "Workspace";

  static String get send => "Send";
  static String get typeMessage => "Type your message...";
  static String get thinking => "Thinking...";
  static String get generating => "Generating...";

  static String get all => "All";
  static String get finished => "Finished";
  static String get failed => "Failed";
  static String get filterBy => "Filter by status";

  static String get screenshot => "Screenshot";
  static String get devices => "Devices";
  static String get noDevices => "No devices found";
  static String get connectDevice => "Connect";
  static String get disconnect => "Disconnect";

  static String get unsavedChanges => "Unsaved changes";
  static String get apiKey => "API Key";
  static String get model => "Model";
  static String get language => "Language";
  static String get theme => "Theme";
  static String get general => "General";

  static String get pathCopied => "Path copied";
  static String get snapshotSaved => "Preview snapshot saved";
  static String get mirrorStarted => "Mirror started";

  static String get offlineMode => "Offline Mode";
  static String get offlineHint => "Some features may be unavailable";
  static String get lastSynced => "Last synced";

  static String nOf(int current, int total) => "$current/$total";
  static String nActive(int n, int total) => "$n/$total active";
  static String nFiles(int n) => "$n file${n == 1 ? '' : 's'}";
  static String nLines(int n) => "$n lines";
  static String nItems(int n) => "$n";
  static String uptime(int seconds) => "${seconds}s";
  static String errorCount(int n) => "Err: $n";
}
