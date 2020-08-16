using Auth0.OidcClient;
using GGShot.Util;
using IdentityModel.OidcClient;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using WPFMediaKit.DirectShow.MediaPlayers;

namespace GGShot
{
    enum MainWindowModes
    {
        Browse,
        Trim,
        Post,
        Busy
    }

    class MainWindowViewModel : BindableBase
    {
        private int m_clipEnd;
        private int m_clipLength;
        private int m_clipCurrent;
        private MainWindowModes m_currentMode = MainWindowModes.Browse;
        DispatcherTimer m_timer;
        Uri m_mediaSource;
        MediaElement m_mediaElement;
        private BrowseItemViewModel m_postItem;
        private string m_postComment;
        private LoginResult m_loginResult;
        private string m_busyText;

        public MainWindowViewModel()
        {
            m_timer = new DispatcherTimer(TimeSpan.FromMilliseconds(100), DispatcherPriority.Normal, OnTimer, Dispatcher.CurrentDispatcher);
            SaveGif = new DelegateCommand(DoSaveGif);
            EscapeCommand = new DelegateCommand(DoEscape);
            PostImage = new DelegateCommand(DoPost);
            LogonCommand = new DelegateCommand(DoLogon);
            RefreshItems();
        }

        internal void UserTextClicked()
        {
            if (IsLoggedIn)
            {
                Process.Start($"http://gameshots.gg/gamer/{UserName}");
            }
            else
            {
                DoLogon();
            }
        }

        private void RefreshItems()
        {
            var capturesDir = Windows.Media.Capture.AppCaptureManager.GetCurrentSettings().AppCaptureDestinationFolder.Path;
            var files = Directory.GetFiles(capturesDir, "*.png").Concat(Directory.GetFiles(capturesDir, "*.mp4"));
            List<BrowseItemViewModel> items = new List<BrowseItemViewModel>();
            foreach (var file in files)
            {
                items.Add(new BrowseItemViewModel(file));
            }

            BrowseItems.Clear();

            foreach (var item in items.OrderByDescending(x => x.CreationTime))
            {
                BrowseItems.Add(item);
            }
        }

        private async void DoLogon()
        {
            var lastMode = CurrentMode;
            BusyText = "Logging in...";
            CurrentMode = MainWindowModes.Busy;
            try
            {
                await DoLogonAsync();
            }
            finally
            {
                CurrentMode = lastMode;
            }
        }

        private async void DoPost()
        {
            CurrentMode = MainWindowModes.Busy;
            if (!IsLoggedIn)
            {
                BusyText = "Logging in...";
                await DoLogonAsync();
            }

            if (IsLoggedIn)
            {
                BusyText = "Posting screenshot...";
                using (HttpClient client = new HttpClient())
                {
                    var imagePath = PostItem.LocalPath;

                    byte[] bytes = PostItem.GetEncodedContentBytes();

                    var fileContent = new ByteArrayContent(bytes);
                    client.DefaultRequestHeaders.Add("authorization", "Bearer " + m_loginResult.AccessToken);
                    var response = await client.PostAsync("http://gameshots.gg/api/createPost", new MultipartFormDataContent()
                    //var response = await client.PostAsync("http://ec2-54-188-110-37.us-west-2.compute.amazonaws.com/api/createPost ", new MultipartFormDataContent()
                    {
                        {fileContent, "file", Path.GetFileName(imagePath)},
                        {new StringContent(PostItem.GameName), "game"},
                        {new StringContent(PostComment), "comment"},
                        {new StringContent(m_loginResult.User.Identity.Name), "username"}
                    });

                    string jsonResponse = await response.Content.ReadAsStringAsync();

                }

                    //client.PostAsync()
            }

            CurrentMode = MainWindowModes.Browse;
        }

        private void DoEscape()
        {
            if (CurrentMode == MainWindowModes.Post)
            {
                CurrentMode = MainWindowModes.Browse;
            }
        }

        internal void ItemDoubleClicked(object sender)
        {
            var senderElement = sender as ListViewItem;
            PostItem = senderElement.DataContext as BrowseItemViewModel;
            if (PostItem != null)
            {
                PostComment = "";
                CurrentMode = MainWindowModes.Post;
            }
        }

        public void SetFile(string uri)
        {
            MediaSource = new Uri(uri);
        }

        private void MediaElement_MediaOpened(object sender, System.Windows.RoutedEventArgs e)
        {
            ClipLength = (int)MediaElement.NaturalDuration.TimeSpan.TotalMilliseconds;
            ClipEnd = ClipLength;
        }

        internal async Task DoLogonAsync()
        {
            Auth0ClientOptions clientOptions = new Auth0ClientOptions
            {
                Domain = "gameshots.us.auth0.com",
                ClientId = "oL1BF2g684pdiJLMw80vwZqeNoPony18",
                RedirectUri = "http://gameshots.gg/callback",
            };
            clientOptions.PostLogoutRedirectUri = clientOptions.RedirectUri;
            
            var extraParameters = new Dictionary<string, string>();
            extraParameters.Add("audience", "http://gameshots.gg/api");
            var client = new Auth0Client(clientOptions);
            m_loginResult = await client.LoginAsync(extraParameters);

            OnPropertyChanged(nameof(LoggedOnUser));
        }

        private void OnTimer(object sender, EventArgs e)
        {
            if ((MediaElement.Position.TotalMilliseconds > ClipEnd) || (MediaElement.Position.TotalMilliseconds < ClipStart))
            {
                MediaElement.Position = TimeSpan.FromMilliseconds(ClipStart);
            }
            ClipCurrent = (int)MediaElement.Position.TotalMilliseconds;
        }

        public MediaElement MediaElement
        {
            get => m_mediaElement;
            set
            {
                if (m_mediaElement != null)
                {
                    m_mediaElement.MediaOpened -= MediaElement_MediaOpened;
                }
                m_mediaElement = value;
                if (m_mediaElement != null)
                {
                    m_mediaElement.MediaOpened += MediaElement_MediaOpened;
                }
            }
        }

        public int ClipLength
        {
            get => m_clipLength;
            set
            {
                SetProperty(ref m_clipLength, value);
            }
        }

        public int ClipCurrent
        {
            get => m_clipCurrent;
            set => SetProperty(ref m_clipCurrent, value);
        }

        public int ClipStart { get; set; } = 0;
        public int ClipEnd
        {
            get => m_clipEnd;
            set => SetProperty(ref m_clipEnd, value);
        }

        public Visibility BrowseVisibility
        {
            get => m_currentMode == MainWindowModes.Browse ? Visibility.Visible : Visibility.Collapsed;
        }

        public Visibility TrimVisibility
        {
            get => m_currentMode == MainWindowModes.Trim ? Visibility.Visible : Visibility.Collapsed;
        }

        public Visibility PostVisibility
        {
            get => m_currentMode == MainWindowModes.Post ? Visibility.Visible : Visibility.Collapsed;
        }

        public Visibility BusyVisibility
        {
            get => m_currentMode == MainWindowModes.Busy ? Visibility.Visible : Visibility.Collapsed;
        }

        private MainWindowModes CurrentMode
        {
            get => m_currentMode;
            set
            {
                m_currentMode = value;
                OnPropertyChanged(nameof(BrowseVisibility));
                OnPropertyChanged(nameof(TrimVisibility));
                OnPropertyChanged(nameof(PostVisibility));
                OnPropertyChanged(nameof(BusyVisibility));
            }
        }

        public Uri MediaSource
        {
            get => m_mediaSource;
            set => SetProperty(ref m_mediaSource, value);
        }

        public ObservableCollection<BrowseItemViewModel> BrowseItems { get; } = new ObservableCollection<BrowseItemViewModel>();
        public BrowseItemViewModel PostItem
        {
            get => m_postItem;
            set => SetProperty(ref m_postItem, value);
        }
        public string PostComment
        {
            get => m_postComment;
            set => SetProperty(ref m_postComment, value);
        }

        public string BusyText
        {
            get => m_busyText;
            set => SetProperty(ref m_busyText, value);
        }

        public DelegateCommand SaveGif { get; private set; }
        public DelegateCommand EscapeCommand { get; private set; }
        public DelegateCommand PostImage { get; private set; }
        public DelegateCommand LogonCommand { get; }

        public bool IsLoggedIn => m_loginResult != null && !m_loginResult.IsError;
        string UserName => m_loginResult.User.Identity.Name;

        public string LoggedOnUser
        {
            get
            {
                if (IsLoggedIn)
                {
                    return UserName;
                }
                return "Log in";
            }
        }

        void DoSaveGif()
        {
            
        }
    }
}
