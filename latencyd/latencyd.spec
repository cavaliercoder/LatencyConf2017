%if %{?el7}
  %define dist .el7
%endif

Name:             latencyd
Version:          1.0.0
Release:          1%{?dist}
Summary:          Demo HTTP server
Group:            Applications/System
License:          MPLv2.0
URL:              https://github.com/cavaliercoder/LatencyConf2017
Source0:          %{name}-%{version}.tar.gz
Source1:          %{name}.service
%{?systemd_requires}
BuildRequires:    systemd
Requires(pre):    /usr/sbin/useradd, /usr/bin/getent
Requires(postun): /usr/sbin/userdel

%description
A demo HTTP server used in my presentation at LatencyConf 2017 to demonstrate
issues that can arise from misconfigured timeouts between server components.

%prep
%setup -q

%build
# nothing to do here

%install
install -d %{buildroot}%{_bindir}/
install -d %{buildroot}%{_sysconfdir}/%{name}/
install -d %{buildroot}%{_sharedstatedir}/%{name}/
install -d %{buildroot}%{_localstatedir}/log/%{name}/
install -d %{buildroot}%{_unitdir}/
install -p -m 755 %{name} %{buildroot}%{_bindir}/%{name}
install -p -m 644 %{SOURCE1} %{buildroot}%{_unitdir}/%{name}.service
cat > %{buildroot}%{_sysconfdir}/%{name}/config.json <<EOF
{
  "logFile": "%{_localstatedir}/log/%{name}/%{name}.log",
  "listenAddr": ":3000",
  "latency": 0,
  "variance": 0,
  "backends": []
}
EOF

%clean
rm -rf %{buildroot}

%pre
# add user account
/usr/bin/getent passwd %{name} || /usr/sbin/useradd -r \
        -d %{_sharedstatedir}/%{name}/ \
        -s /sbin/nologin \
        -c "latencyd service account" \
        %{name}

%post
%systemd_post %{name}.service

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun_with_restart %{name}.service
if [[ "$1" == "0" ]]; then
    # remove user account
    /usr/sbin/userdel %{name}
fi

%files
%attr(0755, root, root) %{_bindir}/%{name}
%attr(0644, root, root) %{_unitdir}/%{name}.service
%attr(0750, root, %{name}) %{_sysconfdir}/%{name}/
%attr(0640, root, %{name}) %config(noreplace) %{_sysconfdir}/%{name}/config.json
%attr(2755, %{name}, %{name}) %{_sharedstatedir}/%{name}/
%attr(0755, %{name}, %{name}) %{_localstatedir}/log/%{name}/

%changelog
* Sun Nov 5 2017 Ryan Armstrong <ryan@cavaliercoder.com> 1.0.0-1
- Initial RPM release
