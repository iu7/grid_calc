using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Net;
using Common;
using Newtonsoft.Json;
using Newtonsoft.Json.Converters;

namespace beacon_backend
{
    class Program
    {
        static void Main(string[] args)
        {
            string port = "666";
            if (args.Length < 1)
                Console.WriteLine("Port was defaulted to " + port);
            else
                port = args[0];

            var uri = "http://*:" + port +'/';

            try
            {
                WebServer ws = new WebServer(dispatcher, uri);
                ws.Run();
                Console.WriteLine(uri + Environment.NewLine + consoleHelp);
                Console.ReadKey();
                ws.Stop();
            }
            catch (Exception e) { }
        }

        struct ServiceState
        {
            public readonly string state;
            public DateTime lastbeat;
            public ServiceState(string state)
            {
                this.state=state;
                lastbeat = DateTime.Now;
            }
        }

        static Dictionary<string, Dictionary<string, ServiceState>> services =
            new Dictionary<string, Dictionary<string, ServiceState>>();

        static string dispatcher(HttpListenerRequest request, HttpListenerResponse response)
        {            
            var pars = request.GetPOSTParams();
            var ipaddr = request.RemoteEndPoint.Address.MapToIPv4().ToString();

            switch (request.Url.Segments.Length)
            {
                case 2: 
                    if (request.Url.AbsolutePath == "/services"
                        || request.Url.AbsolutePath == "/services/")
                        return JsonConvert.SerializeObject(services, new KeyValuePairConverter());
                    else return response.SetError(HttpStatusCode.NotFound, "Endpoint not found");
                case 3:
                    {
                        var type = request.Url.Segments[2].Trim('/');

                        if (request.HttpMethod == "GET")
                            return JsonConvert.SerializeObject(
                                services.Where(kvp => kvp.Key == type).SelectMany(kvp => kvp.Value)
                                .ToDictionary(kvp=>kvp.Key, kvp=>kvp.Value), new KeyValuePairConverter());
                        else if (request.HttpMethod == "POST" &&
                            pars.ContainsKey("port"))
                        {
                            var fulladdr = ipaddr + ':' + pars["port"];

                            if (!services.ContainsKey(type))
                                services.Add(type, new Dictionary<string, ServiceState>());
                            services[type][fulladdr] = new ServiceState(
                                pars.ContainsKey("state") ? pars["state"] : "");

                            return JsonConvert.SerializeObject(new { status = "success", address = fulladdr });
                        }
                        else return response.SetError(HttpStatusCode.MethodNotAllowed, "Requested method is not allowed");
                    }
                case 4:
                    {
                        var type = request.Url.Segments[2].Trim('/');
                        var addr = request.Url.Segments[3].Trim('/');

                        if (request.HttpMethod == "GET")
                        {
                            var got = 
                                services.Where(kvp => kvp.Key == type && kvp.Value.ContainsKey(addr))
                                .Select(kvp => kvp.Value[addr]).ToList();
                            if (got.Count > 0) return JsonConvert.SerializeObject(got.First());
                            else return response.SetError(HttpStatusCode.NotFound, "Requested element was not found");
                        }
                        else if (request.HttpMethod == "PUT")
                        {
                            services[type][addr] = new ServiceState(
                                pars.ContainsKey("state") ? pars["state"] : "");
                            return JsonConvert.SerializeObject(new { status = "success" });
                        }
                        else return response.SetError(HttpStatusCode.MethodNotAllowed, "Requested method is not allowed");
                    }
                default: return response.SetError(HttpStatusCode.NotFound, "Endpoint not found");
            }
        }

        static string consoleHelp =
@"Beacon backend. Endpoints:
/services/type/ POST port
/services/type/ GET
/services/type/address/ POST state
/services/type/address/ GET";
    }
}
