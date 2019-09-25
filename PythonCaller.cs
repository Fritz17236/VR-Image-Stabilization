
using UnityEngine;
using System;
using System.Collections;
using System.Net.Sockets;
using System.Threading;
using System.Net;
using System.Collections.Generic;
using System.Text;


public class PythonCaller : MonoBehaviour
{
    Socket SeverSocket = null;
    Thread Socket_Thread = null;
    bool Socket_Thread_Flag = false;
    private float _w = 0;
    private float _x = 0;
    private float _y = 0;
    private float _z = 0;

    private float _x_pos = 0;
    private float _y_pos = 0;
    private float _z_pos = 0;
    public float x_move_scale = 1;
    public float y_move_scale = 1;
    public float z_move_scale = 1;

    string[] stringSeparators = new string[] { "*TOUCHEND*", "*MOUSEDELTA*", "*Tapped*", "*DoubleTapped*" };

    void Awake()
    {   
        Socket_Thread = new Thread(Dowrk);
        Socket_Thread_Flag = true;
        Socket_Thread.Start();

        Vector3 _init_pos = this.transform.position;
    }

    private void Update()
    {
        this.transform.rotation = new Quaternion(_x, _y, _z, _w);
        this.transform.position = new Vector3(_x_pos*x_move_scale,
                                              _y_pos*y_move_scale,
                                              _z_pos*z_move_scale);

    }

    private void Dowrk()
    {
        //receivedMSG = new string[10];
        SeverSocket = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        IPEndPoint ipep = new IPEndPoint(IPAddress.Any, 9999);
        SeverSocket.Bind(ipep);
        SeverSocket.Listen(10);

        Debug.Log("Socket Standby....");
        Socket client = SeverSocket.Accept();
        Debug.Log("Socket Connected.");

        IPEndPoint clientep = (IPEndPoint)client.RemoteEndPoint;
        NetworkStream recvStm = new NetworkStream(client);
        //tick = 0;

        while (Socket_Thread_Flag)
        {
            byte[] receiveBuffer = new byte[4*7];
            try
            {

                //print (recvStm.Read(receiveBuffer, 0, receiveBuffer.Length));
                if (recvStm.Read(receiveBuffer, 0, receiveBuffer.Length) == 0)
                {
                    // when disconnected , wait for new connection.
                    client.Close();
                    SeverSocket.Close();

                    SeverSocket = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
                    ipep = new IPEndPoint(IPAddress.Any, 10000);
                    SeverSocket.Bind(ipep);
                    SeverSocket.Listen(10);
                    Debug.Log("Socket Standby....");
                    client = SeverSocket.Accept();//client
                    Debug.Log("Socket Connected.");

                    clientep = (IPEndPoint)client.RemoteEndPoint;
                    recvStm = new NetworkStream(client);

                }
                else
                {
                    
                    this._w = System.BitConverter.ToSingle(receiveBuffer,0);
                    this._x = System.BitConverter.ToSingle(receiveBuffer, 4);
                    this._y = System.BitConverter.ToSingle(receiveBuffer, 8);
                    this._z = System.BitConverter.ToSingle(receiveBuffer, 12);

                    this._x_pos = System.BitConverter.ToSingle(receiveBuffer, 16);
                    this._y_pos = System.BitConverter.ToSingle(receiveBuffer, 20);
                    this._z_pos = System.BitConverter.ToSingle(receiveBuffer, 24);

                  

                }

            }

            catch 
            {
                Socket_Thread_Flag = false;
                client.Close();
                SeverSocket.Close();
                continue;
            }

        }

    }

    void OnApplicationQuit()
    {
        try
        {
            Socket_Thread_Flag = false;
            Socket_Thread.Abort();
            SeverSocket.Close();
            Debug.Log("Bye~~");
        }

        catch
        {
            Debug.Log("Error when finished...");
        }
    }

}


