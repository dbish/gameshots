using Auth0.OidcClient;
using GGShot.Util;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using WPFMediaKit.DirectShow.MediaPlayers;

namespace GGShot
{
    class MainWindowViewModel : BindableBase
    {
        private int m_clipEnd;
        private int m_clipLength;
        private int m_clipCurrent;
        private Visibility m_browseVisibility = Visibility.Visible;
        private Visibility m_trimVisibility = Visibility.Hidden;
        DispatcherTimer m_timer;
        Uri m_mediaSource;
        MediaElement m_mediaElement;

        public MainWindowViewModel()
        {
            m_timer = new DispatcherTimer(TimeSpan.FromMilliseconds(100), DispatcherPriority.Normal, OnTimer, Dispatcher.CurrentDispatcher);
            SaveGif = new DelegateCommand(DoSaveGif);
            var capturesDir = Windows.Media.Capture.AppCaptureManager.GetCurrentSettings().AppCaptureDestinationFolder.Path;
            var files = Directory.GetFiles(capturesDir, "*.png");
            foreach (var file in files)
            {
                BrowseItems.Add(new BrowseItemViewModel(file));
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

        internal async void DoLogon()
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
            var loginResult = await client.LoginAsync(extraParameters);
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
            get => m_browseVisibility;
            set => SetProperty(ref m_browseVisibility, value);
        }

        public Visibility TrimVisibility
        {
            get => m_trimVisibility;
            set => SetProperty(ref m_trimVisibility, value);
        }

        public Uri MediaSource
        {
            get => m_mediaSource;
            set => SetProperty(ref m_mediaSource, value);
        }

        public ObservableCollection<BrowseItemViewModel> BrowseItems { get; } = new ObservableCollection<BrowseItemViewModel>();
            
        public DelegateCommand SaveGif { get; private set; }

        void DoSaveGif()
        {
            
        }
    }
}
